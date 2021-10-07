import os
import cv2
import globals as g
import supervisely_lib as sly
from supervisely_lib.io.fs import remove_dir

from queue import Queue
from threading import Thread


class FileVideoStream:
    def __init__(self, path, queueSize=128):
        # initialize the file video stream along with the boolean
        # used to indicate if the thread should be stopped or not
        self.stream = cv2.VideoCapture(path)
        self.stopped = False
        # initialize the queue used to store frames read from
        # the video file
        self.Q = Queue(maxsize=queueSize)

    def start(self):
        # start a thread to read frames from the file video stream
        t = Thread(target=self.update, args=())
        t.daemon = True
        t.start()
        return self

    def update(self):
        # keep looping infinitely
        while True:
            # if the thread indicator variable is set, stop the
            # thread
            if self.stopped:
                return
            # otherwise, ensure the queue has room in it
            if not self.Q.full():
                # read the next frame from the file
                (grabbed, frame) = self.stream.read()
                # if the `grabbed` boolean is `False`, then we have
                # reached the end of the video file
                if not grabbed:
                    self.stop()
                    return
                # add the frame to the queue
                self.Q.put(frame)

    def read(self):
        # return next frame in the queue
        return self.Q.get()

    def more(self):
        # return True if there are still frames in the queue
        return self.Q.qsize() > 0

    def stop(self):
        # indicate that the thread should be stopped
        self.stopped = True


def upload_frames(api: sly.Api, dataset_id, names, images, anns, metas, progress):
    if len(names) > 0:
        new_image_infos = api.image.upload_nps(dataset_id, names, images, metas=metas)
        new_image_ids = [img_info.id for img_info in new_image_infos]
        api.annotation.upload_anns(new_image_ids, anns)
        progress.iters_done_report(len(names))


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


def need_download_video(total_frames, total_annotated_frames):
    frames_threshold = int(total_frames * g.need_download_threshold)
    if total_annotated_frames > frames_threshold:
        return True
    return False


def get_frames_from_video(video_name, video_path, frames_to_convert):
    image_names = []
    images = []
    # vidcap = cv2.VideoCapture(video_path)
    vidcap = FileVideoStream(path=video_path, queueSize=len(frames_to_convert)).start()
    #     progress = sly.Progress(f"Extracting frames from {video_name}", len(frames_to_convert))
    for frame_number in frames_to_convert:
        image_name = video_name + "_" + str(frame_number).zfill(5) + ".jpg"
        image_names.append(image_name)

        # vidcap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        image = vidcap.read()
        images.append(image)
    #         progress.iter_done_report()

    vidcap.stop()
    del vidcap

    return image_names, images


def get_frames_from_api(api, video_id, video_name, frames_to_convert):
    image_names = []
    images = []
    #     progress = sly.Progress(f"Extracting frames from {video_name}", len(frames_to_convert))
    for frame_index in frames_to_convert:
        image_name = video_name + "_" + str(frame_index).zfill(5) + ".jpg"
        image_names.append(image_name)

        image = api.video.frame.download_np(video_id, frame_index)
        images.append(image)
    #         progress.iter_done_report()
    return image_names, images
