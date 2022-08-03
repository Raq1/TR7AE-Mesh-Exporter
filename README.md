# TR7AE-Mesh-Exporter
A Noesis plugin to export custom models to the TR7AE mesh format.

## INSTALLATION:
Download Noesis from here: https://www.richwhitehouse.com/index.php?content=inc_projects.php&showproject=91
Once it is installed, copy fmt_tr7ae.py and paste it in your Noesis root directory/plugins/python.
Now, if you open Noesis, you will be able to open mesh .DRM files, mesh .GNC files, .PCD files and .RAW files.

## What can you do with the exporter?
The exporter allows you to export custom models to Tomb Raider Legend and Anniversary. Both games use the exact same engine, so you can easily port models between the two games.

## Q&A

* Is it possible to replace any model? Not just player Lara?
* The plugin only supports exporting to Anniversary Lara for now. But it is possible to replace any other model with your exported file, with a little bit of hex editing. I explain that at the end of the TR7AE Modding Tutorial.
*
* Is it possible to edit level geometry/collision with this?
* No, level geometry and collision use a different format which the plugin doesn't support as of now. TheIndra is currently working on an experimental level editor, which won't be available anytime soon.
*
* Does the exporter work with Legend Next Gen models?
* No, Legend Next Gen models use a different mesh format which is currently not entirely understood. Maybe I'll consider researching it further in the future, but certainly not now.
*
* What is the vertex/polygon limit of the format?
* The model you want to port to the game must not exceed 21850 vertices, and each individual mesh must not exceed 10922 polygons.

## Thanks to
* [TheIndra55](https://github.com/TheIndra55) for his amazing [Menu Hook](https://github.com/TheIndra55/TRAE-menu-hook) which made debugging extremely faster and easier
* [Joschka](https://forum.xentax.com/memberlist.php?mode=viewprofile&u=82197) for general help with the script, especially the code to write VirtSegments
* [Edness](https://forum.xentax.com/memberlist.php?mode=viewprofile&u=69141) for helping writing UVs in the most accurate way possible
* [alphaZomega](https://github.com/alphazolam) for general help with the script

## Examples

Lara Croft from Tomb Raider: Angel of Darkness ported in Tomb Raider: Anniversary

![image](https://cdn.discordapp.com/attachments/922284054353674273/1004216479950065724/Screenshot_3361.png)
![image](https://cdn.discordapp.com/attachments/922284054353674273/1004216455094620290/Tomb_Raider_Anniversary_Screenshot_2022.08.03_-_04.36.26.39.png)

Lara Croft TR4 outfit custom model ported in Tomb Raider: Anniversary by HenrysArts

![image](https://cdn.discordapp.com/attachments/916875187977326612/1002894311832158298/unknown.png)

Ada Wong ported in Tomb Raider: Legend by EvilLord

![image](https://cdn.discordapp.com/attachments/916875187977326612/1002616571396628662/unknown.png)
