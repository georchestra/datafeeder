# Authorizations

The **authorizations** step of the dataset editor controls who can access a dataset's metadata record and its
published layer, independently of each other:

- **GeoNetwork** rules apply to the metadata record.
- **GeoServer** rules apply to the published data/layer (not available for empty datasets, since they have no
  layer).

For each side, you can:

- toggle it between **public** and **restricted** access
- when restricted, grant **read** or **write** access to specific geOrchestra groups or roles, picked from the same
  group lists used by GeoNetwork and GeoServer

Changes are applied immediately: toggling public/restricted or editing a group's rule calls the backend right away,
which forwards the change to GeoNetwork or GeoServer respectively.
