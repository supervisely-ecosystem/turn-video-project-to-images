import os
import supervisely_lib as sly

my_app = sly.AppService()
api: sly.Api = my_app.public_api

TEAM_ID = int(os.environ['context.teamId'])
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ["modal.state.slyProjectId"])
ONLY_LABELS = os.getenv("modal.state.onlyLabeled").lower() in ('true', '1', 't')

project = api.project.get_info_by_id(PROJECT_ID)
if project is None:
    raise RuntimeError("Project {!r} not found".format(project.name))
if project.type != str(sly.ProjectType.VIDEOS):
    raise TypeError("Project type is {!r}, but have to be {!r}".format(project.type, sly.ProjectType.VIDEOS))

meta_json = api.project.get_meta(project.id)
meta = sly.ProjectMeta.from_json(meta_json)
