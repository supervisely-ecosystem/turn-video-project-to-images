import random
from functools import partial
from io import BytesIO
from time import time

import ffmpeg
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


def need_download_video(total_frames, total_annotated_frames):
    frames_threshold = int(total_frames * g.need_download_threshold)
    return total_annotated_frames > frames_threshold


def read_frame_as_jpeg(in_filename, timestamp):
    out, err = (
        ffmpeg.input(in_filename, ss=timestamp)
            .output("pipe:", vframes=1, format="image2", vcodec="mjpeg")
            .run(capture_stdout=True, quiet=True)
    )
    return out


def get_frames_from_video(video_info, video_path, frames_to_convert, frames_timestamps):
    image_names = []
    images = []
    for frame_number, timestamp in zip(frames_to_convert, frames_timestamps):
        img_bytes = read_frame_as_jpeg(in_filename=video_path,
                                       timestamp=timestamp - video_info.file_meta.get("startTime", 0))
        img = sly.image.read_bytes(img_bytes)
        image_name = f"{video_info.name}_{str(frame_number).zfill(5)}.jpg"
        image_names.append(image_name)
        images.append(img)
    return image_names, images


def get_frames_from_api(api, video_id, video_name, frames_to_convert):
    image_names = []
    images = []
    for frame_index in frames_to_convert:
        image_name = f"{video_name}_{str(frame_index).zfill(5)}.jpg"
        image_names.append(image_name)

        image = api.video.frame.download_np(video_id, frame_index)
        images.append(image)
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
