from src.api.routes.groups_common import GroupItem


class TestGroupItem:
    """Tests for the GroupItem model."""

    def test_group_item_creation(self) -> None:
        item = GroupItem(id="abc", label="My Group")
        assert item.id == "abc"
        assert item.label == "My Group"
