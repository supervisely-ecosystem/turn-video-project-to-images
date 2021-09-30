import os
import cv2
from collections import defaultdict
import supervisely_lib as sly
from supervisely_lib.video_annotation.key_id_map import KeyIdMap

import globals as g
import functions as f


@g.my_app.callback("turn_into_images_project")
@sly.timeit
def turn_into_images_project(api: sly.Api, task_id, context, state, app_logger):
    res_project_name = f"{g.project.name}(images)"
    dst_project = api.project.create(g.WORKSPACE_ID, res_project_name, type=sly.ProjectType.IMAGES, change_name_if_conflict=True)
    api.project.update_meta(dst_project.id, g.meta.to_json())

    key_id_map = KeyIdMap()
    for dataset_name in g.SELECTED_DATASETS:
        dataset = api.dataset.get_info_by_name(g.PROJECT_ID, dataset_name)
        dst_dataset = api.dataset.create(dst_project.id, dataset.name)
        videos = api.video.get_list(dataset.id)
        for batch in sly.batched(videos):
            for video_info in batch:
                name = sly.fs.get_file_name(video_info.name)
                ann_info = api.video.annotation.download(video_info.id)
                ann = sly.VideoAnnotation.from_json(ann_info, g.meta, key_id_map)

                need_optimization = f.optimize_download(video_info.frames_count, len(ann.frames))
                image_paths = None
                if need_optimization is True or g.OPTIONS == "all":
                    video_path = os.path.join(g.video_dir, video_info.name)
                    api.video.download_path(video_info.id, video_path)
                    image_paths = f.vid_to_imgs(dataset_name, video_path, video_info.frames_count)

                frames_to_convert = []
                video_props = []
                video_frame_tags = defaultdict(list)
                f.convert_tags(ann.tags, video_props, video_frame_tags, frames_to_convert)
                object_frame_tags = defaultdict(lambda: defaultdict(list))
                object_props = defaultdict(list)
                for vobject in ann.objects:
                    f.convert_tags(vobject.tags, object_props[vobject.key()], object_frame_tags[vobject.key()], frames_to_convert)
                    vobject_id = key_id_map.get_object_id(vobject.key())
                    f.add_object_id_tag(vobject_id, object_props[vobject.key()])

                if g.OPTIONS == "annotated":
                    frames_to_convert.extend(list(ann.frames.keys()))
                    frames_to_convert = list(dict.fromkeys(frames_to_convert))
                    frames_to_convert.sort()
                else:
                    frames_to_convert = list(range(0, video_info.frames_count))

                names = []
                images = []
                metas = []
                anns = []
                progress = sly.Progress("Video: {!r}".format(video_info.name), len(frames_to_convert))
                for frame_index in frames_to_convert:
                    names.append('{}_frame_{:05d}.jpg'.format(name, frame_index))
                    if need_optimization is False and g.OPTIONS == "annotated":
                        images.append(api.video.frame.download_np(video_info.id, frame_index))
                    else:
                        im = cv2.imread(image_paths[frame_index])
                        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
                        images.append(im)

                    metas.append({
                        "video_id": video_info.id,
                        "video_name": video_info.name,
                        "frame_index": frame_index,
                        "video_dataset_id": video_info.dataset_id,
                        "video_dataset_name": dataset.name,
                        "video_project_id": g.project.id,
                        "video_project_name": g.project.name
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
                        f.upload_and_reset(api, dst_dataset.id, names, images, anns, metas, progress)
                f.upload_and_reset(api, dst_dataset.id, names, images, anns, metas, progress)
    g.my_app.stop()


def main():
    sly.logger.info("Script arguments", extra={
        "TEAM_ID": g.TEAM_ID,
        "WORKSPACE_ID": g.WORKSPACE_ID,
        "PROJECT_ID": g.PROJECT_ID
    })

    # Run application service
    g.my_app.run(initial_events=[{"command": "turn_into_images_project"}])


if __name__ == "__main__":
    sly.main_wrapper("main", main)
