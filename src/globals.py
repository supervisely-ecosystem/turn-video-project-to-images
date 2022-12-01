import json
import os
from distutils.util import strtobool

import supervisely as sly
from dotenv import load_dotenv
from supervisely.io.fs import mkdir

if sly.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))

logger = sly.logger

my_app = sly.AppService()
api: sly.Api = my_app.public_api

TEAM_ID = sly.env.team_id()
WORKSPACE_ID = sly.env.workspace_id()
PROJECT_ID = sly.env.project_id()

SAMPLE_RESULT_FRAMES = bool(strtobool(os.getenv("modal.state.sampleResultFrames")))
if SAMPLE_RESULT_FRAMES:
    FRAMES_STEP = int(os.environ["modal.state.framesStep"])

LOG_LEVEL = str(os.environ["LOG_LEVEL"])

OPTIONS = os.environ["modal.state.Options"]
BATCH_SIZE = int(os.environ["modal.state.batchSize"])

SELECTED_DATASETS = json.loads(
    os.environ["modal.state.selectedDatasets"].replace("'", '"')
)

ALL_DATASETS = os.getenv("modal.state.allDatasets").lower() in ("true", "1", "t")
if ALL_DATASETS:
    SELECTED_DATASETS = [dataset.name for dataset in api.dataset.get_list(PROJECT_ID)]

need_download_threshold = 0.15

storage_dir = os.path.join(my_app.data_dir, "sly_base_sir")
mkdir(storage_dir, True)
video_dir = os.path.join(storage_dir, "video")
mkdir(video_dir)
img_dir = os.path.join(storage_dir, "images")
mkdir(img_dir)

project = api.project.get_info_by_id(PROJECT_ID)
if project is None:
    raise RuntimeError("Project {!r} not found".format(project.name))
if project.type != str(sly.ProjectType.VIDEOS):
    raise TypeError(
        "Project type is {!r}, but have to be {!r}".format(
            project.type, sly.ProjectType.VIDEOS
        )
    )

meta_json = api.project.get_meta(project.id)
meta = sly.ProjectMeta.from_json(meta_json)

if "object_id" not in [tag.name for tag in meta.tag_metas]:
    vobj_id_tag_meta = sly.TagMeta(
        name="object_id",
        value_type=sly.TagValueType.ANY_NUMBER,
        applicable_to=sly.TagApplicableTo.OBJECTS_ONLY,
    )
    meta = meta.add_tag_meta(vobj_id_tag_meta)

if OPTIONS == "annotated" and len(meta.obj_classes) == 0 and len(meta.tag_metas) == 0:
    raise ValueError(
        "Nothing to convert, there are no tags and classes in project {!r}".format(
            project.name
        )
    )
