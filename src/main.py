import os
import supervisely_lib as sly
from supervisely_lib.video_annotation.key_id_map import KeyIdMap

my_app = sly.AppService()

TEAM_ID = int(os.environ['context.teamId'])
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ["modal.state.slyProjectId"])


def upload_and_reset(dataset_id, names, images, anns, progress):
    if len(names) > 0:
        new_image_infos = api.image.upload_nps(dataset_id, names, images)
        new_image_ids = [img_info.id for img_info in new_image_infos]
        api.annotation.upload_anns(new_image_ids, anns)
        progress.iters_done_report(len(names))
    del names[:]
    del images[:]
    del anns[:]


@my_app.callback("turn_into_images_project")
@sly.timeit
def turn_into_images_project(api: sly.Api, task_id, context, state, app_logger):
    project = api.project.get_info_by_id(PROJECT_ID)
    if project is None:
        raise RuntimeError("Project {!r} not found".format(project.name))

    if project.type != str(sly.ProjectType.VIDEOS):
        raise TypeError("Project type is {!r}, but have to be {!r}".format(project.type, sly.ProjectType.VIDEOS))

    meta_json = api.project.get_meta(project.id)
    meta = sly.ProjectMeta.from_json(meta_json)

    #if len(meta.obj_classes) == 0:
    #    raise ValueError("There are no classses in project {!r}".format(SRC_PROJECT_NAME))

    key_id_map = KeyIdMap()
    dst_project = api.project.create(WORKSPACE_ID, DST_PROJECT_NAME, change_name_if_conflict=True)
    api.project.update_meta(dst_project.id, meta_json)

    for dataset in api.dataset.get_list(project.id):
        dst_dataset = api.dataset.create(dst_project.id, dataset.name)
        videos = api.video.get_list(dataset.id)
        for batch in sly.batched(videos):
            for video_info in batch:
                name = sly.fs.get_file_name(video_info.name)
                ann_info = api.video.annotation.download(video_info.id)
                ann = sly.VideoAnnotation.from_json(ann_info, meta, key_id_map)

                progress = sly.Progress("Video: {!r}".format(video_info.name), len(ann.frames))
                image_names = []
                frame_images = []
                dst_anns = []
                for frame in ann.frames:
                    image_names.append('{}_frame_{:05d}.png'.format(name, frame.index))
                    frame_images.append(api.video.frame.download_np(video_info.id, frame.index))
                    labels = [sly.Label(figure.geometry, figure.parent_object.obj_class) for figure in frame.figures]
                    dst_anns.append(sly.Annotation(ann.img_size, labels=labels))

                    if len(image_names) > 10:
                        upload_and_reset(dst_dataset.id, image_names, frame_images, dst_anns, progress)
                upload_and_reset(dst_dataset.id, image_names, frame_images, dst_anns, progress)

    my_app.stop()


def main():
    sly.logger.info("Script arguments", extra={
        "TEAM_ID": TEAM_ID,
        "WORKSPACE_ID": WORKSPACE_ID,
        "PROJECT_ID": PROJECT_ID
    })

    # Run application service
    my_app.run(initial_events=[{"command": "turn_into_images_project"}])


if __name__ == "__main__":
    sly.main_wrapper("main", main)
