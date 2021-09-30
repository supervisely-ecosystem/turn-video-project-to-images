import os
import cv2
import globals as g
import supervisely_lib as sly
from supervisely_lib.io.fs import remove_dir


def upload_and_reset(api: sly.Api, dataset_id, names, images, anns, metas, progress):
    if len(names) > 0:
        new_image_infos = api.image.upload_nps(dataset_id, names, images, metas=metas)
        new_image_ids = [img_info.id for img_info in new_image_infos]
        api.annotation.upload_anns(new_image_ids, anns)
        progress.iters_done_report(len(names))
    del names[:]
    del images[:]
    del anns[:]
    del metas[:]


def convert_tags(tags, prop_container, frame_container, frame_indices=None):
    for video_tag in tags:
        tag = sly.Tag(video_tag.meta, value=video_tag.value, labeler_login=video_tag.labeler_login)
        if video_tag.frame_range is None:
            prop_container.append(tag)
        else:
            for frame_index in range(video_tag.frame_range[0], video_tag.frame_range[1] + 1):
                frame_container[frame_index].append(tag)
                if frame_indices is not None:
                    frame_indices.append(frame_index)


def add_object_id_tag(vobject_id, prop_container):
    vobj_id_tag = sly.Tag(g.vobj_id_tag_meta, value=vobject_id)
    prop_container.append(vobj_id_tag)


def optimize_download(frames_count, frames):
    total = int(frames_count * g.label_treshold_percent)
    if frames >= total:
        need_optimization = True
    else:
        need_optimization = False
    return need_optimization


def vid_to_imgs(dataset_name, video_path, total_frames):
    image_paths = []
    vidcap = cv2.VideoCapture(video_path)
    success, image = vidcap.read()
    count = 1
    progress = sly.Progress("Converting frames to images", total_frames)
    while success:
        image_name = dataset_name + "_" + str(count).zfill(5) + ".png"
        image_path = os.path.join(g.img_dir, image_name)
        image_paths.append(image_path)
        cv2.imwrite(image_path, image)

        success, image = vidcap.read()
        count += 1
        progress.iter_done_report()
    remove_dir(g.video_dir)
    return image_paths
