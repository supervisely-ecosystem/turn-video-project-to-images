import os
from collections import defaultdict
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
    if len(meta.obj_classes) == 0 and len(meta.tag_metas) == 0:
       raise ValueError("Nothing to convert, there are no tags and classes in project {!r}".format(project.name))

    res_project_name = "{}(images)".format(project.name)
    dst_project = api.project.create(WORKSPACE_ID, res_project_name, type=sly.ProjectType.IMAGES, change_name_if_conflict=True)
    api.project.update_meta(dst_project.id, meta_json)

    key_id_map = KeyIdMap()
    for dataset in api.dataset.get_list(project.id):
        dst_dataset = api.dataset.create(dst_project.id, dataset.name)
        videos = api.video.get_list(dataset.id)
        for batch in sly.batched(videos):
            for video_info in batch:
                #@TODO: for debug
                # tagged frames - 372187
                # tagged objects - 371533
                if video_info.id != 371533:
                    continue

                name = sly.fs.get_file_name(video_info.name)
                ann_info = api.video.annotation.download(video_info.id)
                ann = sly.VideoAnnotation.from_json(ann_info, meta, key_id_map)

                #object_key -> frame_index -> list of tags
                object_frame_tags = defaultdict(lambda: defaultdict(list))
                #object_key -> list of properrties
                object_props = defaultdict(list)

                video_props = []
                video_frame_tags = defaultdict(lambda: defaultdict(list))
                for tag in ann.tags:
                    dest_tag_meta = dst_meta.get_tag_meta(tag.name)

                for object in ann.objects:
                    for tag in vobject.tags:
                        if tag.frame_range is None:
                            object_props[object.key()].append(tag)
                        else:
                            tag_without_range = tag.clone()
                            tag_without_range._frame_range = None
                            for frame_index in tag.frame_range:
                                object_frame_tags[object.key()][frame_index].append(tag_without_range)

                progress = sly.Progress("Video: {!r}".format(video_info.name), len(ann.frames))
                image_names = []
                frame_images = []
                dst_anns = []

                for frame in ann.frames:
                    image_names.append('{}_frame_{:05d}.png'.format(name, frame.index))
                    frame_images.append(api.video.frame.download_np(video_info.id, frame.index))

                    labels = []
                    for figure in frame.figures:
                        tags_to_assign = object_props[figure.parent_object.key()].copy()
                        if frame.index in object_frame_tags[figure.parent_object.key()]:
                            tags_to_assign.extend(
                                object_frame_tags[figure.parent_object.key()][frame.index].copy()
                            )

                        cur_label = sly.Label(figure.geometry, figure.parent_object.obj_class, sly.TagCollection(tags_to_assign))
                        labels.append(cur_label)

                    #@old implementation that skips object tags
                    #labels = [sly.Label(figure.geometry, figure.parent_object.obj_class) for figure in frame.figures]

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
