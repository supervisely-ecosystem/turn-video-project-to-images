import os
from collections import defaultdict
import supervisely_lib as sly
from supervisely_lib.video_annotation.key_id_map import KeyIdMap

my_app = sly.AppService()

TEAM_ID = int(os.environ['context.teamId'])
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ["modal.state.slyProjectId"])


def upload_and_reset(api:sly.Api, dataset_id, names, images, anns, metas, progress):
    if len(names) > 0:
        new_image_infos = api.image.upload_nps(dataset_id, names, images, metas=metas)
        new_image_ids = [img_info.id for img_info in new_image_infos]
        api.annotation.upload_anns(new_image_ids, anns)
        progress.iters_done_report(len(names))
    del names[:]
    del images[:]
    del anns[:]
    del metas[:]


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
                name = sly.fs.get_file_name(video_info.name)
                ann_info = api.video.annotation.download(video_info.id)
                ann = sly.VideoAnnotation.from_json(ann_info, meta, key_id_map)
                frames_to_convert = []

                def _convert_tags(tags, prop_container, frame_container, frame_indices=None):
                    for video_tag in tags:
                        tag = sly.Tag(video_tag.meta, value=video_tag.value, labeler_login=video_tag.labeler_login)
                        if video_tag.frame_range is None:
                            prop_container.append(tag)
                        else:
                            for frame_index in range(video_tag.frame_range[0], video_tag.frame_range[1] + 1):
                                frame_container[frame_index].append(tag)
                                if frame_indices is not None:
                                    frame_indices.append(frame_index)

                video_props = []
                video_frame_tags = defaultdict(list)
                _convert_tags(ann.tags, video_props, video_frame_tags, frames_to_convert)

                # object_key -> frame_index -> list of tags
                object_frame_tags = defaultdict(lambda: defaultdict(list))
                # object_key -> list of properrties
                object_props = defaultdict(list)
                for vobject in ann.objects:
                    _convert_tags(vobject.tags, object_props[vobject.key()], object_frame_tags[vobject.key()], frames_to_convert)

                frames_to_convert.extend(list(ann.frames.keys()))
                frames_to_convert = list(dict.fromkeys(frames_to_convert))
                frames_to_convert.sort()

                names = []
                images = []
                metas = []
                anns = []
                progress = sly.Progress("Video: {!r}".format(video_info.name), len(frames_to_convert))
                for frame_index in frames_to_convert:
                    names.append('{}_frame_{:05d}.jpg'.format(name, frame_index))
                    images.append(api.video.frame.download_np(video_info.id, frame_index))

                    #save additional info to image metadata about original video
                    metas.append({
                        "video_id": video_info.id,
                        "video_name": video_info.name,
                        "frame_index": frame_index,
                        "video_dataset_id": video_info.dataset_id,
                        "video_dataset_name":dataset.name,
                        "video_project_id": project.id,
                        "video_project_name": project.name
                    })

                    labels = []
                    frame_annotation = ann.frames.get(frame_index)
                    if frame_annotation is not None:
                        for figure in frame_annotation.figures:
                            tags_to_assign = object_props[figure.parent_object.key()].copy()
                            tags_to_assign.extend(object_frame_tags[figure.parent_object.key()].get(frame_index, []).copy())
                            cur_label = sly.Label(figure.geometry, figure.parent_object.obj_class,
                                                  sly.TagCollection(tags_to_assign))
                            labels.append(cur_label)

                    img_tags = video_props.copy() + video_frame_tags.get(frame_index, []).copy()
                    anns.append(sly.Annotation(ann.img_size, labels=labels, img_tags=sly.TagCollection(img_tags)))

                    if len(names) >= 5:
                        upload_and_reset(api, dst_dataset.id, names, images, anns, metas, progress)
                upload_and_reset(api, dst_dataset.id, names, images, anns, metas, progress)
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
