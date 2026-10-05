"""Tests for dataset export/import across platforms and ownership reassignment."""

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

from src.api.routes.ingestion.integrity_link_admin import (
    delete_integrity_link_admin,
    export_integrity_link,
    import_integrity_link,
    reassign_integrity_link_ownership,
    router,
)
from src.core.config import get_data_schema
from src.core.task_executor import TaskRunInfo, TaskStatus
from src.models.data_import import (
    ImportType,
    IntegrityLinkExport,
    IntegrityLinkImportMode,
    IntegrityLinkImportRequest,
    IntegrityLinkOwnershipRequest,
)
from src.models.integrity_link import IntegrityLink
from src.models.recurrence import RecurrencePreset
from src.services.georchestra import GeorchestraContext

MODULE = "src.api.routes.ingestion.integrity_link_admin"
LINK_ID = uuid4()


def _ctx(admin: bool = True) -> GeorchestraContext:
    return GeorchestraContext(
        username="admin" if admin else "someone",
        roles={"ADMINISTRATOR"} if admin else {"IMPORT"},
        email="",
        firstname="",
        lastname="",
        organization="MEL",
    )


def _link(**overrides: Any) -> IntegrityLink:
    values: dict[str, Any] = {
        "id": LINK_ID,
        "metadata_id": str(LINK_ID),
        "integrity_title": "Voies nommées",
        "integrity_owner": "owner1",
        "integrity_organization": "MEL",
        "integrity_transformation": {"columns": []},
        "source_import_type": ImportType.API,
        "source_url": "https://example.com/wfs",
        "source_layer": "ns:voies",
        "source_protocol": "wfs",
        "final_table_name": "voie_nommee",
        "data_id": "mel:voie_nommee",
    }
    values.update(overrides)
    return IntegrityLink(**values)


def _export(**overrides: Any) -> IntegrityLinkExport:
    values: dict[str, Any] = {
        "id": LINK_ID,
        "metadata_id": str(LINK_ID),
        "integrity_title": "Voies nommées",
        "integrity_owner": "owner1",
        "integrity_organization": "MEL",
        "integrity_transformation": {"columns": []},
        "source_import_type": ImportType.API,
        "source_url": "https://example.com/wfs",
        "source_layer": "ns:voies",
        "source_protocol": "wfs",
        "final_table_name": "voie_nommee",
        "schedule": "0 4 1 * *",
        "preset_id": RecurrencePreset.EVERY_MONTH,
    }
    values.update(overrides)
    return IntegrityLinkExport(**values)


def _schema_per_org(org: str) -> str:
    return org


def _table_only_in_mel(_engine: Any, schema: str, _table: str) -> bool:
    return schema == "mel"


def _table_only_in_data(_engine: Any, schema: str, _table: str) -> bool:
    return schema == "data"


def _session(conflict: IntegrityLink | None = None) -> MagicMock:
    session = MagicMock()
    session.exec.return_value.first.return_value = conflict
    return session


class TestExport:
    def test_export_flags_password_and_resolves_preset(self) -> None:
        link = _link(
            source_password_encrypted="encrypted", schedule=RecurrencePreset.EVERY_DAY.cron
        )
        with patch(f"{MODULE}.load_authorized_integrity_link", return_value=(link, None)):
            result = export_integrity_link(MagicMock(), _ctx(), [], str(LINK_ID))

        assert result.id == LINK_ID
        assert result.has_source_password is True
        assert result.preset_id == RecurrencePreset.EVERY_DAY
        assert result.integrity_transformation == {"columns": []}
        assert "source_password_encrypted" not in result.model_dump()


@pytest.fixture
def import_mocks() -> Iterator[dict[str, MagicMock]]:
    executor = MagicMock()
    executor.trigger_process_task.return_value = TaskRunInfo(
        task_id="process_dag", run_id="run-1", status=TaskStatus.QUEUED
    )
    with (
        patch(f"{MODULE}.table_exists", return_value=False) as table_exists,
        patch(f"{MODULE}.get_data_schema", side_effect=_schema_per_org),
        patch(f"{MODULE}.get_task_executor", return_value=executor),
        patch(f"{MODULE}.encrypt_basic_auth", return_value="encrypted") as encrypt,
        patch(f"{MODULE}.read_table_extent") as read_table_extent,
        patch(f"{MODULE}.publish_final_table", new_callable=AsyncMock) as publish,
    ):
        yield {
            "table_exists": table_exists,
            "executor": executor,
            "encrypt": encrypt,
            "read_table_extent": read_table_extent,
            "publish": publish,
        }


def _metadata_service(record_exists: bool = True) -> MagicMock:
    service = MagicMock()
    service.record_exists.return_value = record_exists
    return service


async def _import(
    request: IntegrityLinkImportRequest,
    session: MagicMock | None = None,
    geoserver: MagicMock | None = None,
    metadata_service: MagicMock | None = None,
    ctx: GeorchestraContext | None = None,
) -> Any:
    return await import_integrity_link(
        request,
        session if session is not None else _session(),
        ctx or _ctx(),
        geoserver or _geoserver(),
        metadata_service or _metadata_service(),
    )


@pytest.mark.asyncio
class TestImportAttach:
    """The data is already on the platform (copied by maelstro): the link is only registered."""

    async def test_existing_table_and_layer_attaches_without_dag(
        self, import_mocks: dict[str, MagicMock]
    ) -> None:
        import_mocks["table_exists"].return_value = True
        geoserver = _geoserver()
        geoserver.layer_exists.return_value = True
        session = _session()
        metadata_service = _metadata_service()
        retrieved_at = datetime(2026, 9, 25, 13, 37, tzinfo=timezone.utc)

        result = await _import(
            IntegrityLinkImportRequest(link=_export(last_retrieval_timestamp=retrieved_at)),
            session,
            geoserver,
            metadata_service,
        )

        assert result.mode == IntegrityLinkImportMode.ATTACH
        assert result.dag_run_id is None
        link = session.add.call_args.args[0]
        assert link.id == LINK_ID
        assert (link.integrity_owner, link.integrity_organization) == ("owner1", "MEL")
        assert link.data_id == "mel:voie_nommee"
        assert link.last_retrieval_timestamp == retrieved_at
        # Not copied unless asked: the dataset starts unscheduled and unpublished
        assert link.schedule is None and link.schedule_enabled is False
        assert link.gn_is_published is False and link.gs_is_published is False
        geoserver.layer_exists.assert_called_once_with("mel", "mel_ds", "voie_nommee")
        import_mocks["publish"].assert_not_called()
        import_mocks["executor"].trigger_process_task.assert_not_called()
        metadata_service.set_record_ownership.assert_called_once_with(link)

    async def test_missing_layer_is_published_from_the_copied_table(
        self, import_mocks: dict[str, MagicMock]
    ) -> None:
        import_mocks["table_exists"].return_value = True
        session = _session()

        result = await _import(IntegrityLinkImportRequest(link=_export()), session)

        assert result.mode == IntegrityLinkImportMode.ATTACH
        import_mocks["read_table_extent"].assert_called_once_with("voie_nommee", "mel")
        publish_args = import_mocks["publish"].call_args.args
        assert publish_args[1] is session.add.call_args.args[0]
        assert publish_args[2:4] == ("voie_nommee", "mel")
        assert session.add.call_args.args[0].last_retrieval_timestamp is not None
        import_mocks["executor"].trigger_process_task.assert_not_called()

    async def test_layer_publication_failure_registers_nothing(
        self, import_mocks: dict[str, MagicMock]
    ) -> None:
        import_mocks["table_exists"].return_value = True
        import_mocks["publish"].side_effect = RuntimeError("geoserver down")
        session = _session()

        with pytest.raises(HTTPException) as exc:
            await _import(IntegrityLinkImportRequest(link=_export()), session)

        assert exc.value.status_code == 502
        session.add.assert_not_called()

    async def test_file_dataset_with_copied_table_is_attached(
        self, import_mocks: dict[str, MagicMock]
    ) -> None:
        import_mocks["table_exists"].return_value = True
        geoserver = _geoserver()
        geoserver.layer_exists.return_value = True

        result = await _import(
            IntegrityLinkImportRequest(link=_export(source_import_type=ImportType.FILE)),
            geoserver=geoserver,
        )

        assert result.mode == IntegrityLinkImportMode.ATTACH

    async def test_empty_dataset_registers_the_link_only(
        self, import_mocks: dict[str, MagicMock]
    ) -> None:
        session = _session()
        geoserver = _geoserver()
        exported = _export(
            source_import_type=ImportType.EMPTY, source_url=None, final_table_name=None
        )

        result = await _import(IntegrityLinkImportRequest(link=exported), session, geoserver)

        assert result.mode == IntegrityLinkImportMode.ATTACH
        session.add.assert_called_once()
        geoserver.layer_exists.assert_not_called()
        import_mocks["table_exists"].assert_not_called()


@pytest.mark.asyncio
class TestImportReprocess:
    """The data is absent: it is re-ingested from its source."""

    async def test_absent_table_reprocesses_from_source(
        self, import_mocks: dict[str, MagicMock]
    ) -> None:
        session = _session()

        result = await _import(IntegrityLinkImportRequest(link=_export()), session)

        assert result.mode == IntegrityLinkImportMode.REPROCESS
        assert result.dag_run_id == "run-1"
        link = session.add.call_args.args[0]
        assert link.last_retrieval_timestamp is None
        kwargs = import_mocks["executor"].trigger_process_task.call_args.kwargs
        assert kwargs.get("staging_table_name") is None
        assert kwargs["final_table_name"] == "voie_nommee"
        assert kwargs["target_schema"] == "mel"
        assert kwargs["source"].source == "https://example.com/wfs"
        assert kwargs["source"].source_type == "API"
        assert kwargs["source"].source_layer == "ns:voies"
        assert "target_schema=mel" in kwargs["success_callback_url"]
        import_mocks["publish"].assert_not_called()

    async def test_copy_recurrence_uses_the_local_preset_cron(
        self, import_mocks: dict[str, MagicMock]
    ) -> None:
        session = _session()
        exported = _export(schedule="0 23 1 * *", preset_id=RecurrencePreset.EVERY_MONTH)

        await _import(IntegrityLinkImportRequest(link=exported, copy_recurrence=True), session)

        link = session.add.call_args.args[0]
        assert link.schedule == RecurrencePreset.EVERY_MONTH.cron
        assert link.schedule_enabled is True

    async def test_source_password_is_encrypted_and_passed_to_the_dag(
        self, import_mocks: dict[str, MagicMock]
    ) -> None:
        session = _session()
        exported = _export(source_username="user", has_source_password=True)

        await _import(IntegrityLinkImportRequest(link=exported, source_password="pwd"), session)

        assert import_mocks["encrypt"].call_args.args[1:] == ("user", "pwd")
        assert session.add.call_args.args[0].source_password_encrypted == "encrypted"
        source = import_mocks["executor"].trigger_process_task.call_args.kwargs["source"]
        assert source.encrypted_credentials == "encrypted"

    async def test_trigger_failure_removes_the_created_link(
        self, import_mocks: dict[str, MagicMock]
    ) -> None:
        import_mocks["executor"].trigger_process_task.side_effect = RuntimeError("airflow down")
        session = _session()

        with pytest.raises(HTTPException) as exc:
            await _import(IntegrityLinkImportRequest(link=_export()), session)

        assert exc.value.status_code == 500
        session.delete.assert_called_once_with(session.add.call_args.args[0])


@pytest.mark.asyncio
class TestImportRejected:
    async def test_file_dataset_without_its_table_is_rejected(
        self, import_mocks: dict[str, MagicMock]
    ) -> None:
        session = _session()

        with pytest.raises(HTTPException) as exc:
            await _import(
                IntegrityLinkImportRequest(link=_export(source_import_type=ImportType.FILE)),
                session,
            )

        assert exc.value.status_code == 400
        assert "copy its data" in exc.value.detail
        session.add.assert_not_called()

    async def test_non_admin_is_forbidden(self, import_mocks: dict[str, MagicMock]) -> None:
        with pytest.raises(HTTPException) as exc:
            await _import(IntegrityLinkImportRequest(link=_export()), ctx=_ctx(admin=False))
        assert exc.value.status_code == 403

    @pytest.mark.parametrize(
        ("overrides", "password", "copy_recurrence"),
        [
            ({"final_table_name": None}, None, False),
            ({"metadata_id": None}, None, False),
            ({"has_source_password": True, "source_username": "user"}, None, False),
            ({}, "pwd", False),  # password without username
            ({"source_import_type": ImportType.FILE}, None, True),  # recurrence of a file
        ],
    )
    async def test_invalid_requests_are_rejected(
        self,
        import_mocks: dict[str, MagicMock],
        overrides: dict[str, Any],
        password: str | None,
        copy_recurrence: bool,
    ) -> None:
        import_mocks["table_exists"].return_value = True
        session = _session()

        with pytest.raises(HTTPException) as exc:
            await _import(
                IntegrityLinkImportRequest(
                    link=_export(**overrides),
                    source_password=password,
                    copy_recurrence=copy_recurrence,
                ),
                session,
            )

        assert exc.value.status_code == 400
        session.add.assert_not_called()

    async def test_conflicting_link_is_rejected(self, import_mocks: dict[str, MagicMock]) -> None:
        session = _session(conflict=_link())

        with pytest.raises(HTTPException) as exc:
            await _import(IntegrityLinkImportRequest(link=_export()), session)

        assert exc.value.status_code == 409
        session.add.assert_not_called()

    async def test_missing_metadata_record_is_rejected(
        self, import_mocks: dict[str, MagicMock]
    ) -> None:
        session = _session()

        with pytest.raises(HTTPException) as exc:
            await _import(
                IntegrityLinkImportRequest(link=_export()),
                session,
                metadata_service=_metadata_service(record_exists=False),
            )

        assert exc.value.status_code == 400
        assert "not found in GeoNetwork" in exc.value.detail
        session.add.assert_not_called()


@pytest.fixture
def reassign_mocks() -> Iterator[dict[str, MagicMock]]:
    console = MagicMock()
    console.get_organization.return_value = {"shortName": "VILLE_ROUBAIX"}
    console.fetch_users_by_usernames.return_value = {"new_owner": "New Owner"}
    with (
        patch(f"{MODULE}.ConsoleService", return_value=console),
        patch(f"{MODULE}.get_data_schema", side_effect=_schema_per_org),
        patch(f"{MODULE}.table_exists", side_effect=_table_only_in_mel) as table_exists,
        patch(f"{MODULE}.read_table_extent") as read_table_extent,
        patch(f"{MODULE}.publish_final_table", new_callable=AsyncMock) as publish,
        patch(f"{MODULE}._move_table") as move_table,
        patch(f"{MODULE}._sync_data_sharing") as sync_data_sharing,
        patch(f"{MODULE}.cancel_dataset_runs") as cancel_runs,
    ):
        yield {
            "console": console,
            "table_exists": table_exists,
            "read_table_extent": read_table_extent,
            "publish": publish,
            "move_table": move_table,
            "sync_data_sharing": sync_data_sharing,
            "cancel_runs": cancel_runs,
        }


async def _reassign(
    link: IntegrityLink,
    owner: str = "new_owner",
    organization: str = "VILLE_ROUBAIX",
    geoserver: MagicMock | None = None,
    metadata_service: MagicMock | None = None,
    ctx: GeorchestraContext | None = None,
) -> Any:
    geoserver = geoserver or _geoserver()
    with patch(f"{MODULE}.load_authorized_integrity_link", return_value=(link, None)):
        return await reassign_integrity_link_ownership(
            str(link.id),
            IntegrityLinkOwnershipRequest(owner=owner, organization=organization),
            MagicMock(),
            ctx or _ctx(),
            [],
            geoserver,
            metadata_service or MagicMock(),
        )


def _geoserver() -> MagicMock:
    geoserver = MagicMock()
    geoserver.layer_exists.return_value = False
    geoserver.public_url = "https://data.example.org/geoserver"
    return geoserver


@pytest.mark.asyncio
class TestReassignOwnership:
    async def test_owner_only_change_does_not_move_data(
        self, reassign_mocks: dict[str, MagicMock]
    ) -> None:
        link = _link()
        metadata_service = MagicMock()

        await _reassign(link, organization="MEL", metadata_service=metadata_service)

        assert (link.integrity_owner, link.integrity_organization) == ("new_owner", "MEL")
        reassign_mocks["move_table"].assert_not_called()
        reassign_mocks["publish"].assert_not_called()
        metadata_service.set_record_ownership.assert_called_once_with(link)

    async def test_organization_change_moves_table_and_layer(
        self, reassign_mocks: dict[str, MagicMock]
    ) -> None:
        link = _link()
        geoserver = _geoserver()
        metadata_service = MagicMock()

        await _reassign(link, geoserver=geoserver, metadata_service=metadata_service)

        assert link.integrity_organization == "VILLE_ROUBAIX"
        reassign_mocks["cancel_runs"].assert_called_once_with(str(LINK_ID))
        reassign_mocks["move_table"].assert_called_once_with("voie_nommee", "mel", "ville_roubaix")
        geoserver.delete_layer.assert_called_once_with("mel", "mel_ds", "voie_nommee")
        geoserver.delete_layer_acl.assert_called_once_with("mel", "voie_nommee")
        publish_args = reassign_mocks["publish"].call_args.args
        assert publish_args[2:4] == ("voie_nommee", "ville_roubaix")
        geoserver.delete_datastore_if_empty.assert_called_once_with("mel", "mel_ds")
        geoserver.delete_workspace_if_empty.assert_called_once_with("mel")
        reassign_mocks["sync_data_sharing"].assert_called_once()
        # The record URLs are left as is, only its ownership follows
        metadata_service.read_schema_from_gn.assert_not_called()
        metadata_service.set_record_ownership.assert_called_once_with(link)

    async def test_publish_failure_restores_previous_location(
        self, reassign_mocks: dict[str, MagicMock]
    ) -> None:
        reassign_mocks["publish"].side_effect = [RuntimeError("geoserver down"), None]
        link = _link()

        with pytest.raises(HTTPException) as exc:
            await _reassign(link)

        assert exc.value.status_code == 502
        assert link.integrity_organization == "MEL"
        assert link.integrity_owner == "owner1"
        assert [c.args for c in reassign_mocks["move_table"].call_args_list] == [
            ("voie_nommee", "mel", "ville_roubaix"),
            ("voie_nommee", "ville_roubaix", "mel"),
        ]
        assert reassign_mocks["publish"].call_args.args[3] == "mel"
        # The restored layer gets its permission rules back
        reassign_mocks["sync_data_sharing"].assert_called_once()

    async def test_existing_layer_in_target_workspace_is_rejected(
        self, reassign_mocks: dict[str, MagicMock]
    ) -> None:
        geoserver = _geoserver()
        geoserver.layer_exists.return_value = True
        link = _link()

        with pytest.raises(HTTPException) as exc:
            await _reassign(link, geoserver=geoserver)

        assert exc.value.status_code == 409
        reassign_mocks["move_table"].assert_not_called()
        assert link.integrity_organization == "MEL"

    async def test_dataset_without_table_only_changes_fields(
        self, reassign_mocks: dict[str, MagicMock]
    ) -> None:
        # table_exists is False outside "mel", and data_id does not point to it either
        link = _link(integrity_organization="OTHER", data_id=None)

        await _reassign(link)

        assert link.integrity_organization == "VILLE_ROUBAIX"
        reassign_mocks["move_table"].assert_not_called()
        reassign_mocks["publish"].assert_not_called()

    async def test_table_left_in_data_schema_is_moved_to_the_org_schema(
        self, reassign_mocks: dict[str, MagicMock]
    ) -> None:
        """Table written before USE_ORG_SCHEMA was enabled: found in data, moved from there."""
        reassign_mocks["table_exists"].side_effect = _table_only_in_data
        geoserver = _geoserver()
        link = _link(integrity_organization="PSC", data_id="psc:voie_nommee")

        await _reassign(link, organization="C2C", geoserver=geoserver)

        reassign_mocks["read_table_extent"].assert_called_once_with("voie_nommee", "data")
        reassign_mocks["move_table"].assert_called_once_with("voie_nommee", "data", "c2c")
        geoserver.delete_layer.assert_called_once_with("psc", "psc_ds", "voie_nommee")
        assert reassign_mocks["publish"].call_args.args[2:4] == ("voie_nommee", "c2c")
        assert link.integrity_organization == "C2C"

    async def test_same_organization_repairs_a_table_left_in_data(
        self, reassign_mocks: dict[str, MagicMock]
    ) -> None:
        """Reassigning to the current org puts back a dataset left in the wrong schema."""
        reassign_mocks["table_exists"].side_effect = _table_only_in_data
        geoserver = _geoserver()
        link = _link(integrity_organization="C2C", data_id="psc:voie_nommee")

        await _reassign(link, organization="C2C", geoserver=geoserver)

        reassign_mocks["move_table"].assert_called_once_with("voie_nommee", "data", "c2c")
        geoserver.delete_layer.assert_called_once_with("psc", "psc_ds", "voie_nommee")
        assert reassign_mocks["publish"].call_args.args[2:4] == ("voie_nommee", "c2c")

    async def test_dataset_already_in_place_is_not_moved(
        self, reassign_mocks: dict[str, MagicMock]
    ) -> None:
        geoserver = _geoserver()

        await _reassign(_link(), organization="MEL", geoserver=geoserver)

        reassign_mocks["move_table"].assert_not_called()
        reassign_mocks["cancel_runs"].assert_not_called()
        geoserver.delete_layer.assert_not_called()

    async def test_without_org_schemas_everything_goes_to_data(
        self, reassign_mocks: dict[str, MagicMock]
    ) -> None:
        """USE_ORG_SCHEMA=false: a table left in an org schema is moved back to data."""
        geoserver = _geoserver()
        link = _link()  # table in "mel", written while USE_ORG_SCHEMA was true

        with (
            patch(f"{MODULE}.get_data_schema", side_effect=get_data_schema),
            patch("src.core.config.get_settings") as mock_settings,
        ):
            mock_settings.return_value.USE_ORG_SCHEMA = False
            await _reassign(link, geoserver=geoserver)

        reassign_mocks["move_table"].assert_called_once_with("voie_nommee", "mel", "data")
        assert reassign_mocks["publish"].call_args.args[2:4] == ("voie_nommee", "data")

    async def test_prefilled_dataset_is_never_moved(
        self, reassign_mocks: dict[str, MagicMock]
    ) -> None:
        link = _link(source_import_type=ImportType.PREFILLED)

        await _reassign(link)

        assert link.integrity_organization == "VILLE_ROUBAIX"
        reassign_mocks["move_table"].assert_not_called()

    @pytest.mark.parametrize("unknown", ["organization", "owner"])
    async def test_unknown_owner_or_organization_is_rejected(
        self, reassign_mocks: dict[str, MagicMock], unknown: str
    ) -> None:
        if unknown == "organization":
            reassign_mocks["console"].get_organization.return_value = None
        else:
            reassign_mocks["console"].fetch_users_by_usernames.return_value = {}
        link = _link()

        with pytest.raises(HTTPException) as exc:
            await _reassign(link)

        assert exc.value.status_code == 400
        assert (link.integrity_owner, link.integrity_organization) == ("owner1", "MEL")

    async def test_non_admin_is_forbidden(self, reassign_mocks: dict[str, MagicMock]) -> None:
        with pytest.raises(HTTPException) as exc:
            await _reassign(_link(), ctx=_ctx(admin=False))
        assert exc.value.status_code == 403


class TestAdminDelete:
    def _delete(self, ctx: GeorchestraContext | None = None, **options: bool) -> MagicMock:
        link = _link()
        with (
            patch(f"{MODULE}.load_authorized_integrity_link", return_value=(link, None)),
            patch(f"{MODULE}.DatasetDeletionService") as service_cls,
        ):
            response = delete_integrity_link_admin(
                str(LINK_ID),
                MagicMock(),
                ctx or _ctx(),
                [],
                MagicMock(),
                MagicMock(),
                **options,
            )
        assert response.status_code == 204
        return service_cls.return_value.delete_dataset

    def test_keeps_layer_and_metadata_by_default(self) -> None:
        route = next(
            r
            for r in router.routes
            if isinstance(r, APIRoute)
            and r.path.endswith("{integrity_link_id}")
            and "DELETE" in r.methods
        )
        defaults = {p.name: p.default for p in route.dependant.query_params}

        assert defaults == {"delete_layer": False, "delete_metadata": False}

    def test_options_are_passed_through(self) -> None:
        delete_dataset = self._delete(delete_layer=True, delete_metadata=True)

        assert delete_dataset.call_args.kwargs == {"delete_layer": True, "delete_metadata": True}

    def test_non_admin_is_forbidden(self) -> None:
        with pytest.raises(HTTPException) as exc:
            self._delete(ctx=_ctx(admin=False), delete_layer=False, delete_metadata=False)
        assert exc.value.status_code == 403
