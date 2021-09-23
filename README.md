<div align="center" markdown>
<img src="https://i.imgur.com/FbUmpLU.png"/>

# Turn videos project into images project

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#How-To-Run">How To Use</a>
</p>


[![](https://img.shields.io/badge/supervisely-ecosystem-brightgreen)](https://ecosystem.supervise.ly/apps/turn-video-project-into-images)
[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervise.ly/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/turn-video-project-into-images)
[![views](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/turn-video-project-into-images&counter=views&label=views)](https://supervise.ly)
[![used by teams](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/turn-video-project-into-images&counter=downloads&label=used%20by%20teams)](https://supervise.ly)
[![runs](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/turn-video-project-into-images&counter=runs&label=runs&123)](https://supervise.ly)

</div>

## Overview

Application key points:  
- Result project name = original name + "(images)" suffix
- Dataset structure and names remain unchanged
- Image name format: "{}_frame_{:05d}.jpg", for example "my_video_frame_00077.jpg"
- Video tags (both properties and frame range tags) are assigned to corresponding images and objects
- Ability to convert only labeled video frames


Application converts all video frames (both tags and figures) to images project or only labeled frames, if checked. Additionaly, information about original video project (`video_id`, `video_name`, `frame_index`, `video_dataset_id`, `video_dataset_name`, `video_project_id`, `video_project_name`) is assigned to every image as metadata. 

Image names have the following format: `{}_frame_{:05d}.jpg`, for example `my_video_frame_00077.jpg`. Video tags (both properties and frame range tags) are assigned to corresponding images and objects

<img src="https://i.imgur.com/7zQQVFA.png"/>

## How To Use

**Step 1:** Add app to your team from Ecosystem if it is not there

**Step 2:** Run app from the context menu of video project

<img src="https://i.imgur.com/WZV7kdJ.png" width="500px"/>

**Step 3:** Wait until the task is finished, new project with `name` = `original name` + `(images)` suffix is created in the same workspace. Link to project is available in task output column
