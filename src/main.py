from collections import defaultdict
from time import time

import supervisely as sly
from supervisely.video_annotation.key_id_map import KeyIdMap

import functions as f

import globals as g


def turn_into_images_project(api: sly.Api):
    res_project_name = f"{g.project.name}(images)"
    dst_project = api.project.create(
        g.workspace_id,
        res_project_name,
        type=sly.ProjectType.IMAGES,
        change_name_if_conflict=True,
    )
    api.project.update_meta(dst_project.id, g.meta.to_json())

    key_id_map = KeyIdMap()
    for dataset_name in g.selected_datasets:
        dataset = api.dataset.get_info_by_name(g.project_id, dataset_name)
        dst_dataset = api.dataset.create(dst_project.id, dataset.name)
        videos = api.video.get_list(dataset.id)
        for batch in sly.batched(videos):
            for video_info in batch:
                general_time = time()
                ann_info = api.video.annotation.download(video_info.id)
                ann = sly.VideoAnnotation.from_json(ann_info, g.meta, key_id_map)
                if (
                    g.options == "annotated"
                    and len(ann.tags) == 0
                    and len(ann.frames) == 0
                ):
                    sly.logger.warn(
                        f"Video {video_info.name} annotation is empty in Dataset {dataset_name}"
                    )
                    continue

                frames_to_convert = []
                video_props = []
                video_frame_tags = defaultdict(list)
                f.convert_tags(
                    ann.tags, video_props, video_frame_tags, frames_to_convert
                )
                object_frame_tags = defaultdict(lambda: defaultdict(list))
                object_props = defaultdict(list)
                for vobject in ann.objects:
                    f.convert_tags(
                        vobject.tags,
                        object_props[vobject.key()],
                        object_frame_tags[vobject.key()],
                        frames_to_convert,
                    )
                    vobject_id = key_id_map.get_object_id(vobject.key())
                    f.add_object_id_tag(vobject_id, object_props[vobject.key()])
                if g.options == "annotated":
                    frames_to_convert.extend(list(ann.frames.keys()))
                    frames_to_convert = list(dict.fromkeys(frames_to_convert))
                    frames_to_convert.sort()
                else:
                    frames_to_convert = list(range(0, video_info.frames_count))

                if g.sample_result_frames:
                    if g.options == "all":
                        frames_to_convert = frames_to_convert[:: g.frames_step]
                    else:
                        frames_to_convert = f.calc_frame_step(
                            frames_to_convert=frames_to_convert,
                            frame_step=g.frames_step,
                        )

                progress = sly.Progress(
                    "Processing video frames: {!r}".format(video_info.name),
                    len(frames_to_convert),
                )

                for batch_index, batch_frames in enumerate(
                    sly.batched(frames_to_convert, batch_size=g.batch_size)
                ):
                    metas = []
                    anns = []
                    local_time = time()
                    images_names, images = f.get_frames_from_api(
                        api, video_info.id, video_info.name, batch_frames, dataset_name
                    )
                    sly.logger.debug(
                        f"extracted {len(batch_frames)} by {time() - local_time} seconds"
                    )

                    for idx, frame_index in enumerate(batch_frames):
                        metas.append(
                            {
                                "video_id": video_info.id,
                                "video_name": video_info.name,
                                "frame_index": frame_index,
                                "video_dataset_id": video_info.dataset_id,
                                "video_dataset_name": dataset.name,
                                "video_project_id": g.project.id,
                                "video_project_name": g.project.name,
                            }
                        )

                        labels = []
                        frame_annotation = ann.frames.get(frame_index)
                        if frame_annotation is not None:
                            for figure in frame_annotation.figures:
                                tags_to_assign = object_props[
                                    figure.parent_object.key()
                                ].copy()
                                tags_to_assign.extend(
                                    object_frame_tags[figure.parent_object.key()]
                                    .get(frame_index, [])
                                    .copy()
                                )
                                cur_label = sly.Label(
                                    figure.geometry,
                                    figure.parent_object.obj_class,
                                    sly.TagCollection(tags_to_assign),
                                )
                                labels.append(cur_label)

                        img_tags = (
                            video_props.copy()
                            + video_frame_tags.get(frame_index, []).copy()
                        )

                        frame_np = images[idx]
                        height, width, _ = frame_np.shape
                        img_size = (height, width)

                        anns.append(
                            sly.Annotation(
                                img_size,
                                labels=labels,
                                img_tags=sly.TagCollection(img_tags),
                            )
                        )

                    f.upload_frames(
                        api,
                        dst_dataset.id,
                        images_names,
                        images,
                        anns,
                        metas,
                        f"{batch_index}/{int(len(frames_to_convert) / g.batch_size)}",
                    )
                    progress.iters_done_report(len(images_names))

                sly.logger.info(
                    f"video {video_info.name} converted in {time() - general_time} seconds"
                )


if __name__ == "__main__":
    turn_into_images_project(g.api)
