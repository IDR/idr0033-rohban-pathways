#! /usr/bin/env python
#
# Attach original cell/nuclei outline masks uploaded as part of the submission
# to the relevant well samples for idr0033
#
# For each well sample of the illumination corrected plates, the masks are
# stored under 20170214-original/images_segmented_outlines with the following
# sub-paths:
# * {plate}/{well}_s{field}_CellOutlines.png
# * {plate}/{well}_s{field}_NucleiOutlines.png
# where plate is the plate number, well is the well position e.g. a02 and
# field is the 1-indexed field of view


import argparse
import logging
import omero
from omero.cli import cli_login
from omero.gateway import BlitzGateway
from omero.model import FileAnnotationI
from omero_upload import upload_ln_s
import os.path
import sys


OMERO_DATA_DIR = "/data/OMERO"
NAMESPACE = 'openmicroscopy.org/idr/analysis/original'
MIMETYPE = 'image/png'
FILESET_PATH = "/uod/idr/filesets/idr0033-rohban-pathways"
log = logging.getLogger()


def upload_and_link(conn, attachment, image):
    fo = upload_ln_s(conn.c, attachment, OMERO_DATA_DIR, MIMETYPE)
    fa = FileAnnotationI()
    fa.setFile(fo._obj)
    fa.setNs(omero.rtypes.rstring(NAMESPACE))
    fa = conn.getUpdateService().saveAndReturnObject(fa)
    fa = omero.gateway.FileAnnotationWrapper(conn, fa)
    image.linkAnnotation(fa)


def get_seg_paths(well, index):
    SEG_PATH = FILESET_PATH + "/20170214-original/images_segmented_outlines"
    TYPES = ["Cell", "Nuclei"]
    plate = well.getParent()
    p = plate.getName()[:-16]
    r = plate.getRowLabels()[well.row].lower()
    c = "%02d" % plate.getColumnLabels()[well.column]
    i = index + 1
    paths = tuple(f"{SEG_PATH}/{p}/{r}{c}_s{i}_{t}Outlines.png" for t in TYPES)
    for p in paths:
        assert os.path.exists(p), f"{p} does not exist"
    return paths


def get_corrected_wells(conn):
    wells = []
    screen = conn.getObject('Screen', attributes={
        'name': 'idr0033-rohban-pathways/screenA'})
    for plate in screen.listChildren():
        pn = plate.getName()
        if not pn.endswith("_illum_corrected"):
            log.info(f"Skipping plate {pn}")
            continue
        wells.extend(list(plate.listChildren()))
    return wells


def process_well(conn, well, dry_run=True):
    FIELDS = 9
    wellpos = well.getWellPos()
    plate = well.getParent().getName()
    log.info(f"Processing well {wellpos} of plate {plate}")
    for i in range(FIELDS):
        cell_path, nuclei_path = get_seg_paths(well, i)
        if not dry_run:
            log.info(f"Uploading and linking {cell_path}")
            upload_and_link(conn, cell_path, well.getImage(i))
        if not dry_run:
            log.info(f"Uploading and linking {nuclei_path}")
            upload_and_link(conn, nuclei_path, well.getImage(i))


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--verbose', '-v', action='count', default=0,
        help='Increase the command verbosity')
    parser.add_argument(
        '--quiet', '-q', action='count', default=0,
        help='Decrease the command verbosity')
    parser.add_argument(
        '--dry-run', '-n', action='store_true',
        help='Run command in dry-run mode')
    args = parser.parse_args(argv)

    default_level = logging.INFO - 10 * args.verbose + 10 * args.quiet
    logging.basicConfig(level=default_level)
    with cli_login() as c:
        conn = BlitzGateway(client_obj=c.get_client())
        for well in get_corrected_wells(conn):
            process_well(conn, well, dry_run=args.dry_run)


if __name__ == "__main__":
    main(sys.argv[1:])
