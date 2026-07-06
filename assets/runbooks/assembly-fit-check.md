# Assembly fit check

1. Create or update `cad.project.json` with parts, transforms, and `bbox_mm` estimates.
2. `@CADExpert` renders each part SCAD to STL.
3. `@ManufacturingExpert` runs assembly validation (`/api/cad/assembly/validate`).
4. Resolve fit issues (overlap, missing SCAD) before export.
5. Export combined STLs or individual parts for multi-material print.
