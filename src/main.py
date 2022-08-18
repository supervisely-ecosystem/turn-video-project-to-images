import io
import os
from collections import defaultdict
import supervisely as sly
from supervisely.video_annotation.key_id_map import KeyIdMap

import globals as g
import functions as f

from time import time
import sys


@g.my_app.callback("turn_into_images_project")
@sly.timeit
def turn_into_images_project(api: sly.Api, task_id, context, state, app_logger):
    res_project_name = f"{g.project.name}(images)"
    dst_project = api.project.create(g.WORKSPACE_ID, res_project_name, type=sly.ProjectType.IMAGES,
                                     change_name_if_conflict=True)
    api.project.update_meta(dst_project.id, g.meta.to_json())

    key_id_map = KeyIdMap()
    for dataset_name in g.SELECTED_DATASETS:
        dataset = api.dataset.get_info_by_name(g.PROJECT_ID, dataset_name)
        dst_dataset = api.dataset.create(dst_project.id, dataset.name)
        videos = api.video.get_list(dataset.id)
        for batch in sly.batched(videos):
            for video_info in batch:
                general_time = time()
                ann_info = api.video.annotation.download(video_info.id)
                ann = sly.VideoAnnotation.from_json(ann_info, g.meta, key_id_map)
                if g.OPTIONS == "annotated" and len(ann.tags) == 0 and len(ann.frames) == 0:
                    g.my_app.logger.warn(f"Video {video_info.name} annotation is empty in Dataset {dataset_name}")
                    continue

                need_download_video = f.need_download_video(video_info.frames_count, len(ann.frames))
                video_path = None
                if need_download_video or g.OPTIONS == "all":
                    local_time = time()
                    video_path = os.path.join(g.video_dir, video_info.name)

                    progress_cb = f.get_progress_cb("Downloading video", int(video_info.file_meta['size']),
                                                    is_size=True)
                    api.video.download_path(video_info.id, video_path, progress_cb=progress_cb)
                    g.logger.info(f'video {video_info.name} downloaded in {time() - local_time} seconds')

                frames_to_convert = []
                video_props = []
                video_frame_tags = defaultdict(list)
                f.convert_tags(ann.tags, video_props, video_frame_tags, frames_to_convert)
                object_frame_tags = defaultdict(lambda: defaultdict(list))
                object_props = defaultdict(list)
                for vobject in ann.objects:
                    f.convert_tags(vobject.tags, object_props[vobject.key()], object_frame_tags[vobject.key()],
                                   frames_to_convert)
                    vobject_id = key_id_map.get_object_id(vobject.key())
                    f.add_object_id_tag(vobject_id, object_props[vobject.key()])
                if g.OPTIONS == "annotated":
                    frames_to_convert.extend(list(ann.frames.keys()))
                    frames_to_convert = list(dict.fromkeys(frames_to_convert))
                    frames_to_convert.sort()
                else:
                    frames_to_convert = list(range(0, video_info.frames_count))

                progress = sly.Progress("Processing video frames: {!r}".format(video_info.name), len(frames_to_convert))

                # total_images_size = 0
                for batch_index, batch_frames in enumerate(sly.batched(frames_to_convert, batch_size=g.BATCH_SIZE)):
                    metas = []
                    anns = []
                    if need_download_video or g.OPTIONS == "all":
                        local_time = time()
                        images_names, images = f.get_frames_from_video(video_info.name, video_path, batch_frames)

                        g.logger.debug(f'extracted {len(batch_frames)} by {time() - local_time} seconds')

                        """
                        too slow calculations, for extreme debug


                        images_size = f.calculate_batch_size(images) / (1024 * 1024)  # in MegaBytes

                        g.logger.debug(f'batch size: {images_size} MB')
                        g.logger.debug(f'mean item size: {images_size / len(images)} MB')
                        total_images_size += images_size
                        """

                    else:
                        images_names, images = f.get_frames_from_api(api, video_info.id, video_info.name, batch_frames)
                    for frame_index in batch_frames:
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
                                tags_to_assign.extend(
                                    object_frame_tags[figure.parent_object.key()].get(frame_index, []).copy())
                                cur_label = sly.Label(figure.geometry, figure.parent_object.obj_class,
                                                      sly.TagCollection(tags_to_assign))
                                labels.append(cur_label)

                        img_tags = video_props.copy() + video_frame_tags.get(frame_index, []).copy()
                        anns.append(sly.Annotation(ann.img_size, labels=labels, img_tags=sly.TagCollection(img_tags)))

                    if g.LOG_LEVEL == 'debug':
                        f.distort_frames(images)
                        g.logger.debug(f'{len(images)} frames distorted')

                    f.upload_frames(api, dst_dataset.id, images_names, images, anns, metas,
                                    f'{batch_index}/{int(len(frames_to_convert) / g.BATCH_SIZE)}')
                    progress.iters_done_report(len(images_names))

                # g.logger.debug(f'total images size for video: {total_images_size} MB')
                g.logger.info(f'video {video_info.name} converted in {time() - general_time} seconds')
    g.my_app.stop()


@g.my_app.callback("stop")
@sly.timeit
def stop(api: sly.Api, task_id, context, state, app_logger):
    g.my_app.stop()


def main():
    if g.LOG_LEVEL == 'debug':
        g.logger.debug(f'DEBUG MODE ACTIVATED, we will add 50 random pixels to distort images')

    sly.logger.info("Script arguments", extra={
        "TEAM_ID": g.TEAM_ID,
        "WORKSPACE_ID": g.WORKSPACE_ID,
        "PROJECT_ID": g.PROJECT_ID
    })

    # Run application service
    g.my_app.run(initial_events=[{"command": "turn_into_images_project"}])


if __name__ == "__main__":
    sly.main_wrapper("main", main)
