# How to send the data file for a dataset you already registered

*A guide for MFL focal points and contributors — updated 2026-09-14.*

Your dataset is described in the MOSAIC catalog, but the file itself still sits
on a personal Drive, OneDrive or laptop — so nobody else can actually open it.
MOSAIC's second phase is about making the open datasets genuinely usable: each file
quality-checked and published with a permanent, citable link. This is how you hand a file over.

MOSAIC stays a coordination network and metadata system: the upload folder is a
**staging step, not storage**. Once your file is there, we agree with you where
it should live permanently, and your catalog record points there. Files that
already have a good home stay where they are — we only link to them.

## What you need first

A **Record ID** — the `MFL-2026-0XX` code of the dataset in the catalog. If your
dataset isn't registered yet, register it first
([How to register a dataset](HOW_TO_REGISTER_DATASETS.md)); a loose file with no
record can't be filed against anything.

The **folder link** is sent to you by email — it is not published here. It opens a
MOSAIC folder on CGIAR's SharePoint and needs your **CGIAR account** to sign in. No CGIAR
account? See the note at the end of the next section.

## Send it — step by step (about five minutes)

1. **Name your file(s) first.** Put the Record ID at the start, then a short name:

   ```
   MFL-2026-023__tree-mapping.zip
   MFL-2026-038__soil-resource.tif
   MFL-2026-020__localities.geojson
   ```

   The Record ID is how the file finds its record. A file without it has to be chased down by
   email.

2. **Zip anything that is more than one file.** A shapefile is *not* one file: `.shp` alone is
   useless without `.shx`, `.dbf` and `.prj`. Zip the whole set and keep the original names
   inside. Same for tiled rasters or a folder of CSVs. **One zip per dataset** — not six datasets
   in one zip.

3. **Open the link from the email and sign in with your CGIAR account.**

4. Click **Upload → Files** (or drag and drop your files into the folder). That's it — drop us a
   line when it's up.

**No CGIAR account?** Reply to the email with a share link to the files from your own drive
(Google Drive, OneDrive, Dropbox…), or ask for a guest invitation to the folder. **Files larger
than a few GB**, or a folder that won't let you upload: reply to the email and we'll arrange
another way.

## Please don't send

- **Anything not openly licensed.** If the dataset is Internal or Restricted,
  keep the file — we record how someone requests access instead. If the access
  level in the catalog is wrong, tell us and we'll correct the record.
- **Datasets that already have a public URL or DOI.** Send the link, not the
  file: duplicating a dataset that already has a home creates two versions that
  drift apart. This includes anything from an external provider (NASA/USGS,
  Copernicus, national statistics portals) — MOSAIC links to the source.
- **Personal or sensitive data**: individual survey responses with identifiers,
  or precise locations of threatened species or sacred sites. If a dataset needs
  aggregating or blurring before it can be shared, send the aggregated version
  and say what you did.

## What happens next

1. We check the file opens, matches its record, and carries the license it
   claims.
2. Your record is updated with the real file details, so the catalog stops
   saying "on a shared drive".
3. We come back to you to agree where the dataset lives permanently — usually a
   citable deposit that gives you a DOI, so you keep the credit and can cite it
   yourself. The catalog record then links to that.

Questions, or a file too big or too sensitive for the link:
**Lizeth Llanos — l.llanos@cgiar.org**, subject "MOSAIC data file".
