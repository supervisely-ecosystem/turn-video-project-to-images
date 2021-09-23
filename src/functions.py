import supervisely_lib as sly


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
