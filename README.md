<div align="center" markdown>
<img src="https://i.imgur.com/FbUmpLU.png"/>

# Videos project to images project

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

Transforms supervisely **videos** project to supervisely **images** project. 

Application key points:  
- Backward compatible with [Images project to videos project](https://app.supervise.ly/apps/ecosystem/images-project-to-videos-project)
- Result project name = original name + "(images)" suffix
- Dataset structure and names remain unchanged
- Image name format: "{}_frame_{:05d}.jpg", for example "my_video_frame_00077.jpg"
- Video tags (both properties and frame range tags) are assigned to corresponding images and objects
- Ability to convert only labeled video frames
- Information about original video project (`video_id`, `video_name`, `frame_index`, `video_dataset_id`, `video_dataset_name`, `video_project_id`, `video_project_name`) is assigned to every image as metadata. 


<img src="https://i.imgur.com/7zQQVFA.png"/>

# How To Use 

1. Add [Videos project to images project](https://app.supervise.ly/apps/ecosystem/turn-video-project-into-images) to your team from Ecosystem.

<img data-key="sly-module-link" data-module-slug="supervisely-ecosystem/turn-video-project-into-images" src="https://i.imgur.com/9gUzdYM.png" width="350px" style='padding-bottom: 20px'/>  

2. Run app from the context menu of **Videos Project**:

<img src="https://i.imgur.com/rckw2ZP.png" width="100%"/>

3. Check the box if you need only annotated video frames and press the `Run` button.
 
<div align="center" markdown>
<img src="https://i.imgur.com/Ynf5lmF.png" width="500"/>
</div>


# Results

After running the application, you will be redirected to the `Tasks` page.  
Once application processing has finished, your project will be available.  
Click on the `project name` to proceed to it.

<img src="https://i.imgur.com/ADEnjJd.png"/>
