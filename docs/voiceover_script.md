# Procedural Room Maps in Houdini 21 - Voiceover Script

01. Hi everyone, and welcome.
In this tutorial, we'll explore a procedural pipeline for generating interior Room Maps, leveraging the power of Houdini 21.

02. A little while ago, I started working on my animated film, which features several large cityscapes like this one.
As you can see, the buildings look a bit lifeless, with that mechanically repetitive look to the simple and pretty identical window polygons.
I wanted to find an efficient way to breathe life into these facades.

03. In this tutorial, I'm going to show you my solution: a procedural pipeline for generating interior Room Maps, built entirely in Houdini 21 with Solaris, Karma XPU, PDG, and Copernicus.
We won't be going through every single node click-by-click.
This will be a high-level production workflow breakdown, focusing on the key architectural decisions.

04. Let's dive in and begin with a bit of background.
SideFX first introduced the Karma Room Map shader in Houdini 20.0. This is a brilliant tool for creating the illusion of detailed interiors without modeling any geometry.
It's a shader that projects a texture map onto a window primitive, and for medium to distant shots, the effect is incredibly convincing and efficient.

05. To truly sell this illusion across an entire city block, however, you need a vast library of unique room maps.
As SideFX themselves mentioned in a Houdini 20.0 keynote presentation, they used PDG to generate a set of 25 maps for their own presentation.
This concept of a 'content factory' was powerful, but it's in Houdini 21 that this idea truly comes to fruition.
Thanks to the synergy between the now robust Copernicus context for procedural texturing and the major performance improvements in Karma XPU for rendering, I was able to design the elegant and highly automated pipeline that we're exploring today.

06. First, let’s take a closer look at what the Karma Room Map shader is and how it works.
In essence, it’s a projection shader that maps a cross-shaped texture of an interior onto a surface, creating a convincing illusion of a 3D room.
Using slices from S1 to S4, you can further enhance the parallax and sense of depth.
These slices can include furniture, people silhouettes, curtains, and other objects like lamps, plants, etc.
The primary advantage of this technique is, of course, performance.
Instead of heavy geometry inside the room, we use a single texture map.
Depending on the viewing angle, Karma intelligently reveals the correct portion of the interior.

07. Here is what the map layout looks like on screen.
You can see the five core areas forming the cross, which correspond to the walls, floor and ceiling.
In the corners, we have the four slots for the slices I just mentioned.
The basic setup uses one map that’s projected onto a plane.
To work correctly, these interior maps must be EXR files with an alpha channel and with a specific fixed layout to ensure that each room element appears on the correct wall.

08. The system is flexible.
It's possible to use a single map for multiple adjacent windows via a room-identifying attribute.
Although this will cause the texture to stretch, this distortion can be compensated for using the shader's scaling parameters in Solaris.

09. But the real power of the Karma Room Map Shader lies in its randomization capabilities.
The principle is simple: the more unique maps you feed into it, the more organic and non-repetitive your building facades will look.
The official Houdini documentation already provides a detailed guide on how to set up this randomization — in other words, how to apply an existing library of iterior maps.
Since this tutorial isn't a step-by-step guide on applying the shader, I won't be covering that process. I'll simply leave a link to the official documentation in the description below.
Our focus today is on the crucial step that comes before that: the actual creation of that vast library of unique maps from scratch.

10. So, let me walk you through my process.
Before we dive into the details, it's important to define our scope.
Of course, a real-world building contains a wide variety of interior spaces: kitchens, bedrooms, and, perhaps, commercial spaces like shops on the ground floor.
For this tutorial, however, we will focus exclusively on creating living rooms as an example.
The workflow we establish here will serve as a foundational template that you can easily adapt to generate any other type of interior later on.

11. I've structured this entire workflow into a clear, three-stage pipeline.
First, Asset Creation.
In this stage, we'll build a library of all the USD components for our interiors: walls with procedural wallpapers, slices with furniture, lamps, and other props.
Second, Scene Assembly and Rendering.
Here, we'll use Solaris to procedurally assemble these components into unique room variations and render each wall, floor, ceiling, and slice separately using Karma XPU.
And finally, the third stage.
We'll take our rendered pieces into the Copernicus context and automate the final assembly of the Room Map textures.

12. So, our first step is to create a simple box to serve as the room geometry.
The real catalyst for this entire workflow is Houdini 21's powerful Copernicus context.
This is what allows us to move beyond static, pre-made textures and instead build a fully procedural pipeline for generating intricate wallpaper patterns.
For the purposes of this video, I've created four distinct variations, but the system we're building is capable of producing a almost endless library.

13. Next, I moved on to creating the core components for the room's interior.
For this task, Component Builder is an incredibly powerful tool for quickly structuring a large number of geometry options and material variations into a single, robust USD-asset.
For anyone looking for a brilliant step-by-step introduction to USD asset creation in Solaris, the 'FOUNDATIONS: Solaris Market' series on the SideFX website is the essential starting point.
And for those who want an even deeper technical dive into the Component Builder, the original 2022 masterclass also remains a fantastic resource.
You can think of this present tutorial as a production-focused application of the principles taught in both.

14. To give you a concrete example, I show a table component based on the principles from that masterclass.
This single table component contains three geometry variants (round, square, and rectangular) and two distinct material options: one with black legs, and another with metallic ones.
The "Explore Variants" LOP node in Solaris is perfect for quality control, as it allows you to quickly cycle through and verify every possible combination.
Once I confirmed that all six variants were correctly configured, I saved the component as a USD file, ready for the next step.

15. The assembly process itself was straightforward: I populated USD hierarchy of the room by defining a specific prim path for each wall and slice, and then brought in the appropriate component using a USD reference.
A clean and logical USD hierarchy was critical for this stage, as it would later allow me to easily isolate and render each part of the room individually.

16. For specific USD assemblies, like the procedurally arranged books on the bookshelf, I drew inspiration from the SideFX tutorial series 'USD Asset Building with Solaris' by Peter Arcara.
It's an excellent resource for a deep, technical understanding of how to structure pipeline-ready USD assets.

17. To further enhance the procedural variety, I also automated some of the finer details within the scene.
For instance, I linked the material variant of the chandelier to the color tint of the room's primary light source.
This way, a change in the light fixture automatically drives a corresponding change in the room's ambiance.
As another small touch, the pictures on the walls are randomized from a small library of images.
I'll be curious to see if anyone in the comments can guess their origin!

18. Of course, this procedural approach comes with a few deliberate constraints.
For instance, not every living room in real life is cube-shaped with furniture arranged in this way.
This is a necessary trade-off between realism and the shader's specific Room Map texture layout.
Since the map is essentially a cube unfolded into a cross shape, our room geometry must match that structure.
After all, our objective is not hero interiors for close-ups, but a vast library of performant, art-directable backgrounds designed for the medium and distant shots of a large-scale cityscape.

19. Moving on.
With the scene assembled, the next step was to configure the individual render passes in Solaris for each wall and slice.
And this is where our clean USD hierarchy was a huge help.
The "Render Geometry Setting" LOP node makes this process incredibly efficient.
By targeting the specific prim paths we established earlier, I could effortlessly isolate each component for rendering, effectively pruning the rest of the complex scene with a single node.

20. The final step in this stage was to configure PDG to render out all our component variations.
And here, I have to admit I went a bit overboard with the number of components I'd made.
If I had actually iterated through every possible combination, I would have ended up with tens of thousands of textures — which was way more than I really needed.
It would have been much smarter if I had calculated the total number of combinations in advance.

21. So, to control the variations procedurally, I used a few Wedge nodes within the TOP network.
Each Wedge node creates and iterates through a range of attribute values — for instance, one attribute to cycle through the wallpaper types, another for the lighting setups, and a third for the curtain variations.
I then connected these upstream from all the ROP Fetch nodes that we had previously set up for each wall and slice, allowing PDG to automate the entire rendering process.

22. Now for the final compositing stage, where Copernicus plays its second key role.
The manual process would be to take the nine rendered images for each room variation — the five walls and four slices — load them into a Copernicus network, and arrange them into the final cross-shaped layout using simple 2D transforms.
But the real elegance of this pipeline is that we can fully automate this stage as well.
By feeding the very same Wedge attributes that drove our renders into the compositing network, PDG can automatically fetch the correct set of nine images for each variation, assemble them in Copernicus, and export the final map to a dedicated folder.
I also added a step to generate a quick PNG-preview image for each of them.
And just like that, this system generated 256 unique room map variations, complete with different wallpapers, lighting states, and curtain styles.
The final, crucial step was to batch-rename all the output maps to conform to the UDIM sequence format required by the Room Map Shader's documentation. This means each file must have the same base name, appended with a UDIM token, which is essentially a sequential number like 1001, 1002, and so on.
That is the complete pipeline for building a scalable, procedural library of interior Room Maps.

23. With that done, I now have a robust and reusable asset library.
For any future project, like this one, I can simply point Houdini to this directory, and the Room Map shader setup will automatically randomize the assignment of these detailed interiors across all the window surfaces.

24. So, let's return to those shots from the beginning of this tutorial.
Here they are again, but with our new library applied.
There's a little more life in there now, don't you think?

25. Looking ahead, I plan to expand this library with dedicated sets for bedrooms, kitchens, and even large, multi-window office spaces.
While the core pipeline for any new room type will still rely on the same core tools: Solaris, Karma XPU, Copernicus, and PDG — the process of creating the specific furniture and prop components for each is a deep dive of its own.
If a follow-up video focusing on the asset creation for any of those specific room types is something you would like to see, please do let me know in the comments below!

26. This pipeline represents my current approach to visualizing buildings for medium and distant shots.
However, I'm a firm believer that any procedural system can always be refined and improved.
That's why I'm genuinely curious to hear your own thoughts or ideas for optimization, so please feel free to share them in the comments.
And, of course, if you have any questions about the process, I'll do my best to answer every one.

27. It’s all good!
Peace!
