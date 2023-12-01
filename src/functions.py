import random
from functools import partial
from io import BytesIO
from time import sleep, time

import supervisely as sly

import globals as g


def upload_frames(api: sly.Api, dataset_id, names, images, anns, metas, current_batch):
    if len(names) > 0:
        local_time = time()

        # progress_cb = get_progress_cb(f"Processing batch {current_batch}:", len(images), is_size=False)
        new_image_infos = api.image.upload_nps(
            dataset_id, names, images, metas=metas, progress_cb=None
        )
        new_image_ids = [img_info.id for img_info in new_image_infos]
        api.annotation.upload_anns(new_image_ids, anns)
        g.logger.info(f"batch uploaded in {time() - local_time} seconds")


def convert_tags(tags, prop_container, frame_container, frame_indices=None):
    for video_tag in tags:
        tag = sly.Tag(
            video_tag.meta, value=video_tag.value, labeler_login=video_tag.labeler_login
        )
        if video_tag.frame_range is None:
            prop_container.append(tag)
        else:
            for frame_index in range(
                video_tag.frame_range[0], video_tag.frame_range[1] + 1
            ):
                frame_container[frame_index].append(tag)
                if frame_indices is not None:
                    frame_indices.append(frame_index)


def add_object_id_tag(vobject_id, prop_container):
    vobj_id_tag = sly.Tag(g.vobj_id_tag_meta, value=vobject_id)
    prop_container.append(vobj_id_tag)


def download_frames_with_retry(api: sly.Api, video_id, frames_to_convert):
    retry_cnt = 5
    curr_retry = 0
    while curr_retry <= retry_cnt:
        try:
            images = api.video.frame.download_nps(video_id, frames_to_convert)
            if len(images) != len(frames_to_convert):
                raise RuntimeError(f"Downloaded {len(images)} frames, but {len(frames_to_convert)} expected.")
            return images
        except Exception as e:
            curr_retry += 1
            if curr_retry <= retry_cnt:
                sleep(2 ** curr_retry)
                sly.logger.warn(f"Failed to download frames, retry {curr_retry} of {retry_cnt}... Error: {e}")
    raise RuntimeError(f"Failed to download frames with ids {frames_to_convert}. Check your data and try again. Error: {e}")


def get_frames_from_api(api: sly.Api, video_id, video_name, frames_to_convert, dataset_name):
    if g.project.custom_data.get("original_images") is not None:
        image_names = []
        for frame in frames_to_convert:
            image_name = g.project.custom_data["original_images"][dataset_name][
                str(frame)
            ]
            image_names.append(image_name)
    else:
        image_names = [
            f"{video_name}_{str(frame_index).zfill(5)}.jpg"
            for frame_index in frames_to_convert
        ]
    images = download_frames_with_retry(api, video_id, frames_to_convert)
    return image_names, images


def get_progress_cb(message, total, is_size=False):
    progress = sly.Progress(message, total, is_size=is_size)
    progress_cb = partial(
        update_progress, api=g.api, task_id=g.my_app.task_id, progress=progress
    )
    progress_cb(0)
    return progress_cb


def update_progress(count, api: sly.Api, task_id, progress: sly.Progress):
    progress.iters_done_report(count)
    _update_progress_ui(api, task_id, progress)


def _update_progress_ui(
    api: sly.Api, task_id, progress: sly.Progress, stdout_print=False
):
    if progress.need_report():
        fields = [
            {"field": "data.progressName", "payload": progress.message},
            {"field": "data.currentProgressLabel", "payload": progress.current_label},
            {"field": "data.totalProgressLabel", "payload": progress.total_label},
            {"field": "data.currentProgress", "payload": progress.current},
            {"field": "data.totalProgress", "payload": progress.total},
        ]
        api.app.set_fields(task_id, fields)
        if stdout_print is True:
            progress.report_if_needed()


def distort_frames(images):
    random.seed(time())
    for index, image in enumerate(images):
        for _ in range(50):
            image[
                random.randint(0, image.shape[0] - 1),
                random.randint(0, image.shape[1] - 1),
                random.randint(0, image.shape[2] - 1),
            ] = random.randint(0, 255)


def calculate_batch_size(images_batch):
    from PIL import Image

    batch_size = 0
    for image in images_batch:
        img = Image.fromarray(image)
        img_file = BytesIO()
        img.save(img_file, "jpeg")
        img_file_size_jpeg = img_file.tell()
        batch_size += img_file_size_jpeg
    return batch_size


def calc_frame_step(frames_to_convert, frame_step):
    res = [frames_to_convert[0]]
    for i in frames_to_convert[1:]:
        if i - res[-1] >= frame_step:
            res.append(i)
    return res
