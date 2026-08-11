# RnD: Room Map Shader (L1) вЂ” Implementation Plan

**Jira Project**: KRM
**Status**: In Progress
**Last Updated**: 2026-02-04

---

> [!IMPORTANT]
> **Session operating rules!** Chat is in Russian; documentation, commits, and code comments are in British English. A question is not a command to perform work.

---

## рџ§© EPIC: Text (KRM-1)

**Status**: вњ… Done | **Priority**: Medium

### вњ… [KRM-2] Draft Text

**Status**: вњ… Done | **Priority**: Medium
**Logged**: 2h

### вњ… [KRM-3] Rewrite

**Status**: вњ… Done | **Priority**: Medium
**Logged**: 2h

### вњ… [KRM-4] Final

**Status**: вњ… Done | **Priority**: Medium
**Logged**: 2h

---

## рџ§© EPIC: VO (KRM-5)

**Status**: вњ… Done | **Priority**: Medium

### вњ… [KRM-10] Draft and Finalise Tutorial Script (English)

**Status**: вњ… Done | **Priority**: Medium
**Objective**: Write, review, and finalise the complete English script for the
  'Procedural Room Maps in Houdini 21' tutorial video. Ensure all technical
  details are accurate and the narrative flow is clear.

### вњ… [KRM-11] Generate AI Pronunciation Reference Audio (ElevenLabs)

**Status**: вњ… Done | **Priority**: Medium
**Objective**: Utilise ElevenLabs text-to-speech service to generate a reference
  audio track from the finalised script. This serves as a guide for correct
  English pronunciation and intonation during the actual voice-over recording.

### вњ… [KRM-12] Record Voice-Over (VO)

**Status**: вњ… Done | **Priority**: Medium
**Objective**: Record the full voice-over narration for the tutorial based on
  the finalised script, using the AI-generated audio as a pronunciation
  reference. Aim for clear articulation and appropriate pacing.

### вњ… [KRM-13] Post-Process VO Recording (Noise Reduction)

**Status**: вњ… Done | **Priority**: Medium
**Objective**: Clean up the raw VO recording. Apply noise reduction techniques
  to remove background noise and ensure audio clarity. Perform basic levelling
  if necessary.

### вњ… [KRM-14] Import Processed VO into Premiere Pro Project

**Status**: вњ… Done | **Priority**: Medium
**Objective**: Set up the main video editing project in Adobe Premiere Pro.
  Import the cleaned and processed voice-over track onto the timeline as the
  foundational audio layer.

---

## рџ§© EPIC: Tutorial: Shots (KRM-7)

**Status**: вЏёпёЏ To Do | **Priority**: Medium

### вЏёпёЏ [KRM-15] Shot 01 Intro

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 01 IntroTime: 00:00:00:00 Duration: 00:00:11:00Content:Hi
  everyone, and welcome.In this video, we'll explore a procedural pipeline for
  generating interior Room Maps, leveraging the power of Houdini 21.

### вЏёпёЏ [KRM-16] Shot 02 Cityscapes Need Life

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 02 Cityscapes Need LifeTime: 00:00:11:00 Duration:
  00:00:20:00Content:A little while ago, I started working on my animated film,
  which features several large cityscapes like this one.As you can see, the
  buildings look a bit lifeless, with that mechanically repetitive look to the
  simple and pretty identical window polygons.I wanted to find an efficient way
  to breathe life into these facades.

### вЏёпёЏ [KRM-17] Shot 03 Introducing the Procedural Pipeline

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 03 Introducing the Procedural PipelineTime: 00:00:31:00
  Duration: 00:00:23:10Content:In this video, I'm going to show you my solution:
  a procedural pipeline for generating interior Room Maps, built entirely in
  Houdini 21 with Solaris, Karma XPU, PDG, and Copernicus.We won't be going
  through every single node click-by-click.This will be a high-level production
  workflow breakdown, focusing on the key architectural decisions.

### вЏёпёЏ [KRM-18] Shot 04 Karma Room Map Shader Intro

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 04 Karma Room Map Shader IntroTime: 00:00:54:10 Duration:
  00:00:24:02Content:Let's dive in and begin with a bit of background.SideFX
  first introduced the Karma Room Map shader in Houdini 20.0.This is a brilliant
  tool for creating the illusion of detailed interiors without modeling any
  geometry.It's a shader that projects a texture map onto a window primitive,
  and for medium to distant shots, the effect is incredibly convincing and
  efficient.

### вЏёпёЏ [KRM-19] Shot 05 Need for Large Map Library

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 05 Need for Large Map LibraryTime: 00:01:18:12 Duration:
  00:00:38:18Content:To truly sell this illusion across an entire city block,
  however, you need a vast library of unique room maps.As SideFX themselves
  mentioned in a Houdini 20.0 keynote presentation, they used PDG to generate a
  set of 25 maps for their own presentation.This concept of a 'content factory'
  was powerful, but it's in Houdini 21 that this idea truly comes to
  fruition.Thanks to the synergy between the now robust Copernicus context for
  procedural texturing and the major performance improvements in Karma XPU for
  rendering, I was able to design the elegant and highly automated pipeline that
  we're exploring today.

### вЏёпёЏ [KRM-20] Shot 06 How the Shader Works

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 06 How the Shader WorksTime: 00:01:57:05 Duration:
  00:00:15:03Content:First, let's take a closer look at what the Karma Room Map
  shader is and how it works.In essence, it's a projection shader that maps a
  cross-shaped texture of an interior onto a surface, creating a convincing
  illusion of a 3D room.

### вЏёпёЏ [KRM-21] Shot 07 Using Depth Slices

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 07 Using Depth SlicesTime: 00:02:12:08 Duration:
  00:00:13:07Content:Using slices from S1 to S4, you can further enhance the
  parallax and sense of depth.These slices can include furniture, people
  silhouettes, curtains, and other objects like lamps, plants, etc.

### вЏёпёЏ [KRM-22] Shot 08 Performance Advantage Explained

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 08 Performance Advantage ExplainedTime: 00:02:25:15
  Duration: 00:00:14:14Content:The primary advantage of this technique is, of
  course, performance.Instead of heavy geometry inside the room, we use a single
  texture map.Depending on the viewing angle, Karma intelligently reveals the
  correct portion of the interior.

### вЏёпёЏ [KRM-23] Shot 09 Room Map Layout Overview

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 9 Room Map Layout OverviewTime: 00:02:40:04 Duration:
  00:00:14:08Content:Here is what the map layout looks like on screen.You can
  see the five core areas forming the cross, which correspond to the walls,
  floor and ceiling.In the corners, we have the four slots for the slices I just
  mentioned.

### вЏёпёЏ [KRM-24] Shot 10 Map Format & Requirements

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 10 Map Format & RequirementsTime: 00:02:54:12 Duration:
  00:00:15:04Content:The basic setup uses one map that's projected onto a
  plane.To work correctly, these interior maps must be EXR files with an alpha
  channel and with a specific fixed layout to ensure that each room element
  appears on the correct wall.

### вЏёпёЏ [KRM-25] Shot 11 Reusing Maps via Attributes

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 11 Reusing Maps via AttributesTime: 00:03:09:16 Duration:
  00:00:07:15Content:The system is flexible.It's possible to use a single map
  for multiple adjacent windows via a room-identifying attribute.

### вЏёпёЏ [KRM-26] Shot 12 Fixing Texture Distortion

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 12 Fixing Texture DistortionTime: 00:03:17:06 Duration:
  00:00:08:02Content:Although this will cause the texture to stretch, this
  distortion can be compensated for using the shader's scaling parameters in
  Solaris.

### вЏёпёЏ [KRM-27] Shot 13 Power of Randomization

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 13 Power of RandomizationTime: 00:03:25:08 Duration:
  00:00:33:06Content:But the real power of the Karma Room Map Shader lies in its
  randomization capabilities.The principle is simple: the more unique maps you
  feed into it, the more organic and non-repetitive your building facades will
  look.The official Houdini documentation already provides a detailed guide on
  how to set up this randomization вЂ” in other words, how to apply an existing
  library of iterior maps.Since this video isn't a step-by-step guide on
  applying the shader, I won't be covering that process.I'll simply leave a link
  to the official documentation in the description below.

### вЏёпёЏ [KRM-28] Shot 14 Focus on Map Creation

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 14 Focus on Map CreationTime: 00:03:58:14 Duration:
  00:00:11:21Content:Our focus today is on the crucial step that comes before
  that: the actual creation of that vast library of unique maps from scratch.So,
  let me walk you through my process.

### вЏёпёЏ [KRM-29] Shot 15 Defining Project Scope

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 15 Defining Project ScopeTime: 00:04:10:10 Duration:
  00:00:14:12Content:Before we dive into the details, it's important to define
  our scope.Of course, a real-world building contains a wide variety of interior
  spaces: kitchens, bedrooms, and, perhaps, commercial spaces like shops on the
  ground floor.

### вЏёпёЏ [KRM-30] Shot 16 Focusing on Living Rooms

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 16 Focusing on Living RoomsTime: 00:04:24:22 Duration:
  00:00:14:07Content:For this video, however, we will focus exclusively on
  creating living rooms as an example.The workflow we establish here will serve
  as a foundational template that you can easily adapt to generate any other
  type of interior later on.

### вЏёпёЏ [KRM-31] Shot 17 Three-Stage Pipeline Overview

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 17 Three-Stage Pipeline OverviewTime: 00:04:39:04 Duration:
  00:00:39:15Content:I've structured this entire workflow into a clear, three-
  stage pipeline.First, Asset Creation. In this stage, we'll build a library of
  all the USD components for our interiors: walls with procedural wallpapers,
  slices with furniture, lamps, and other props.Second, Scene Assembly and
  Rendering. Here, we'll use Solaris to procedurally assemble these components
  into unique room variations and render each wall, floor, ceiling, and slice
  separately using Karma XPU.And finally, the third stage.We'll take our
  rendered pieces into the Copernicus context and automate the final assembly of
  the Room Map textures.

### вЏёпёЏ [KRM-32] Shot 18 Creating Base Room Geometry

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 18 Creating Base Room GeometryTime: 00:05:18:19 Duration:
  00:00:05:08Content:So, our first step is to create a simple box to serve as
  the room geometry.

### вЏёпёЏ [KRM-33] Shot 19 Copernicus Context for Textures

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 19 Copernicus Context for TexturesTime: 00:05:24:02
  Duration: 00:00:25:08Content:The real catalyst for this entire workflow is
  Houdini 21's powerful Copernicus context.This is what allows us to move beyond
  static, pre-made textures and instead build a fully procedural pipeline for
  generating intricate wallpaper patterns.For the purposes of this video, I've
  created four distinct variations, but the system we're building is capable of
  producing a almost endless library.

### вЏёпёЏ [KRM-34] Shot 20 Building Core USD Components

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 20 Building Core USD ComponentsTime: 00:05:49:10 Duration:
  00:00:16:06Content:Next, I moved on to creating the core components for the
  room's interior.For this task, Component Builder is an incredibly powerful
  tool for quickly structuring a large number of geometry options and material
  variations into a single, robust USD-asset.

### вЏёпёЏ [KRM-35] Shot 21 Learning from SideFX Foundations

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 21 Learning from SideFX FoundationsTime: 00:06:05:16
  Duration: 00:00:12:05Content:For anyone looking for a brilliant step-by-step
  introduction to USD asset creation in Solaris, the 'FOUNDATIONS: Solaris
  Market' series on the SideFX website is the essential starting point.

### вЏёпёЏ [KRM-36] Shot 22 Advanced USD Masterclass Reference

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 22 Advanced USD Masterclass ReferenceTime: 00:06:17:21
  Duration: 00:00:17:04Content:And for those who want an even deeper technical
  dive into the Component Builder, the original 2022 masterclass also remains a
  fantastic resource.You can think of this present video as a production-focused
  application of the principles taught in both.

### вЏёпёЏ [KRM-37] Shot 23 Example: Table Component Variants

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 23 Example: Table Component VariantsTime: 00:06:35:00
  Duration: 00:00:37:22Content:To give you a concrete example, I show a table
  component based on the principles from that masterclass.This single table
  component contains three geometry variants (round, square, and rectangular)
  and two distinct material options: one with black legs, and another with
  metallic ones.The "Explore Variants" LOP node in Solaris is perfect for
  quality control, as it allows you to quickly cycle through and verify every
  possible combination.Once I confirmed that all six variants were correctly
  configured, I saved the component as a USD file, ready for the next step.

### вЏёпёЏ [KRM-38] Shot 24 Assembling USD Room Hierarchy

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 24 Assembling USD Room HierarchyTime: 00:07:12:22 Duration:
  00:00:22:02Content:The assembly process itself was straightforward: I
  populated USD hierarchy of the room by defining a specific prim path for each
  wall and slice, and then brought in the appropriate component using a USD
  reference.A clean and logical USD hierarchy was critical for this stage, as it
  would later allow me to easily isolate and render each part of the room
  individually.

### вЏёпёЏ [KRM-39] Shot 25 Procedural Bookshelf Example

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 25 Procedural Bookshelf ExampleTime: 00:07:34:24 Duration:
  00:00:18:19Content:For specific USD assemblies, like the procedurally arranged
  books on the bookshelf, I drew inspiration from the SideFX tutorial series
  'USD Asset Building with Solaris' by Peter Arcara.It's an excellent resource
  for a deep, technical understanding of how to structure pipeline-ready USD
  assets.

### вЏёпёЏ [KRM-40] Shot 26 Automating Interior Details

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 26 Automating Interior DetailsTime: 00:07:53:18 Duration:
  00:00:19:07Content:To further enhance the procedural variety, I also automated
  some of the finer details within the scene.For instance, I linked the material
  variant of the chandelier to the color tint of the room's primary light
  source.This way, a change in the light fixture automatically drives a
  corresponding change in the room's ambiance.

### вЏёпёЏ [KRM-41] Shot 27 Randomizing Wall Pictures

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 27 Randomizing Wall PicturesTime: 00:08:13:00 Duration:
  00:00:10:01Content:As another small touch, the pictures on the walls are
  randomized from a small library of images.I'll be curious to see if anyone in
  the comments can guess their origin!

### вЏёпёЏ [KRM-42] Shot 28 Balancing Realism and Constraints

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 28 Balancing Realism and ConstraintsTime: 00:08:23:01
  Duration: 00:00:35:24Content:Of course, this procedural approach comes with a
  few deliberate constraints.For instance, not every living room in real life is
  cube-shaped with furniture arranged in this way.This is a necessary trade-off
  between realism and the shader's specific Room Map texture layout.Since the
  map is essentially a cube unfolded into a cross shape, our room geometry must
  match that structure.After all, our objective is not hero interiors for close-
  ups, but a vast library of performant, art-directable backgrounds designed for
  the medium and distant shots of a large-scale cityscape.

### вЏёпёЏ [KRM-43] Shot 29 Setting Up Render Passes

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 29 Setting Up Render PassesTime: 00:08:59:00 Duration:
  00:00:08:12Content:Moving on.With the scene assembled, the next step was to
  configure the individual render passes in Solaris for each wall and slice.

### вЏёпёЏ [KRM-44] Shot 30 Efficient Isolation via LOPs

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 30 Efficient Isolation via LOPsTime: 00:09:07:12 Duration:
  00:00:21:15Content:And this is where our clean USD hierarchy was a huge
  help.The "Render Geometry Setting" LOP node makes this process incredibly
  efficient.By targeting the specific prim paths we established earlier, I could
  effortlessly isolate each component for rendering, effectively pruning the
  rest of the complex scene with a single node.

### вЏёпёЏ [KRM-45] Shot 31 PDG Rendering Configuration

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 31 PDG Rendering ConfigurationTime: 00:09:29:02 Duration:
  00:00:06:09Content:The final step in this stage was to configure PDG to render
  out all our component variations.

### вЏёпёЏ [KRM-46] Shot 32 Managing Too Many Variations

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 32 Managing Too Many VariationsTime: 00:09:35:11 Duration:
  00:00:20:03Content:And here, I have to admit I went a bit overboard with the
  number of components I'd made.If I had actually iterated through every
  possible combination, I would have ended up with tens of thousands of textures
  вЂ” which was way more than I really needed.It would have been much smarter if I
  had calculated the total number of combinations in advance.

### вЏёпёЏ [KRM-47] Shot 33 Controlling Variants with Wedges

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 33 Controlling Variants with WedgesTime: 00:09:55:14
  Duration: 00:00:18:06Content:So, to control the variations procedurally, I
  used a few Wedge nodes within the TOP network.Each Wedge node creates and
  iterates through a range of attribute values вЂ” for instance, one attribute to
  cycle through the wallpaper types, another for the lighting setups, and a
  third for the curtain variations.

### вЏёпёЏ [KRM-48] Shot 34 Automating Renders via PDG

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 34 Automating Renders via PDGTime: 00:10:13:20 Duration:
  00:00:10:09Content:I then connected these upstream from all the ROP Fetch
  nodes that we had previously set up for each wall and slice, allowing PDG to
  automate the entire rendering process.

### вЏёпёЏ [KRM-49] Shot 35 Copernicus Compositing Setup

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 35 Copernicus Compositing SetupTime: 00:10:24:04 Duration:
  00:00:20:04Content:Now for the final compositing stage, where Copernicus plays
  its second key role.The manual process would be to take the nine rendered
  images for each room variation вЂ” the five walls and four slices вЂ” load them
  into a Copernicus network, and arrange them into the final cross-shaped layout
  using simple 2D transforms.

### вЏёпёЏ [KRM-50] Shot 36 Full Automation of Assembly

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 36 Full Automation of AssemblyTime: 00:10:44:08 Duration:
  00:00:26:08Content:But the real elegance of this pipeline is that we can fully
  automate this stage as well.By feeding the very same Wedge attributes that
  drove our renders into the compositing network, PDG can automatically fetch
  the correct set of nine images for each variation, assemble them in
  Copernicus, and export the final map to a dedicated folder.I also added a step
  to generate a quick PNG-preview image for each of them.

### вЏёпёЏ [KRM-51] Shot 37 Generating 256 Room Variations

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h

### вЏёпёЏ [KRM-52] Shot 38 Renaming Files for UDIM Format

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 38 Renaming Files for UDIM FormatTime: 00:11:19:18
  Duration: 00:00:25:00Content:The final, crucial step was to batch-rename all
  the output maps to conform to the UDIM sequence format required by the Room
  Map Shader's documentation. This means each file must have the same base name,
  appended with a UDIM token, which is essentially a sequential number like
  1001, 1002, and so on. That is the complete pipeline for building a scalable,
  procedural library of interior Room Maps.

### вЏёпёЏ [KRM-53] Shot 39 Reusable Room Map Library

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 39 Reusable Room Map LibraryTime: 00:11:44:18 Duration:
  00:00:16:17Content:With that done, I now have a robust and reusable asset
  library. For any future project, like this one, I can simply point Houdini to
  this directory, and the Room Map shader setup will automatically randomize the
  assignment of these detailed interiors across all the window surfaces.

### вЏёпёЏ [KRM-54] Shot 40 Final Shots вЂ” Applied Results

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 40 Final Shots вЂ” Applied ResultsTime: 00:12:01:10 Duration:
  00:00:10:19Content:So, let's return to those shots from the beginning of this
  video. Here they are again, but with our new library applied. There's a little
  more life in there now, don't you think?

### вЏёпёЏ [KRM-55] Shot 41 Expanding to More Room Types

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 41 Expanding to More Room TypesTime: 00:12:12:04 Duration:
  00:00:08:00Content:Looking ahead, I plan to expand this library with dedicated
  sets for bedrooms, kitchens, and even large, multi-window office spaces.

### вЏёпёЏ [KRM-56] Shot 42 Future Pipeline Adaptations

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 42 Future Pipeline AdaptationsTime: 00:12:20:04 Duration:
  00:00:25:23Content:While the core pipeline for any new room type will still
  rely on the same core tools: Solaris, Karma XPU, Copernicus, and PDG вЂ” the
  process of creating the specific furniture and prop components for each is a
  deep dive of its own. If a follow-up video focusing on the asset creation for
  any of those specific room types is something you would like to see, please do
  let me know in the comments below!

### вЏёпёЏ [KRM-57] Shot 43 Current Visualization Approach

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 43 Current Visualization ApproachTime: 00:12:46:02
  Duration: 00:00:06:08Content:This pipeline represents my current approach to
  visualizing buildings for medium and distant shots.

### вЏёпёЏ [KRM-58] Shot 44 Room for Optimization

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 44 Room for OptimizationTime: 00:12:52:10 Duration:
  00:00:15:00Content:However, I'm a firm believer that any procedural system can
  always be refined and improved. That's why I'm genuinely curious to hear your
  own thoughts or ideas for optimization, so please feel free to share them in
  the comments.

### вЏёпёЏ [KRM-59] Shot 45 Q&A and Feedback Invitation

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 45 Q&A and Feedback InvitationTime: 00:13:07:10 Duration:
  00:00:05:14Content:And, of course, if you have any questions about the
  process, I'll do my best to answer every one.

### вЏёпёЏ [KRM-60] Shot 46 Outro вЂ” Peace

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Shot: 46 Outro вЂ” PeaceTime: 00:13:12:24 Duration:
  00:00:07:01Content:It's all good! Peace!

---

## рџ§© EPIC: Analyse Karma Room Map Shader (KRM-61)

**Status**: Review | **Priority**: Medium

### вњ… [KRM-79] Geometry Context Analysis (SOP)

**Status**: вњ… Done | **Priority**: Medium | **Estimate**: 2h
**Objective**: Analyse attribute creation and setup in Geometry context.
**Logged**: 2h

### вњ… [KRM-80] Material Context Analysis (Solaris/LOP)

**Status**: вњ… Done | **Priority**: Medium | **Estimate**: 2h
**Objective**: Study Material Library setup and parameter exposure in
  Solaris/LOP context.
**Logged**: 1h

### вњ… [KRM-81] Application Layer: USD Binding

**Status**: вњ… Done | **Priority**: Medium | **Estimate**: 2h
**Objective**: Analyse USD material binding and primvar mapping.

### вњ… [KRM-82] Shader Internals: VEX/MaterialX Deep Dive

**Status**: вњ… Done | **Priority**: Medium | **Estimate**: 2h
**Objective**: Deep dive into VEX and MaterialX shader nodes in both Geometry
  and Solaris contexts.

### вњ… [KRM-83] Initial Documentation & Knowledge Base Setup

**Status**: вњ… Done | **Priority**: Medium | **Estimate**: 2h
**Objective**: Mine Houdini documentation and formulate VEX to MDL translation
  strategy.
**Logged**: 2h

### вњ… [KRM-84] Formulate Final VEX-to-MDL Strategy Document

**Status**: вњ… Done | **Priority**: Medium | **Estimate**: 4h
**Objective**: Synthesize findings from technical analysis tasks (KRM-79..82)
  into a cohesive translation strategy document.

---

## рџ§© EPIC: MDL API & Mathematics Research (KRM-62)

**Status**: рџ”„ In Progress | **Priority**: Medium

### рџ”„ [KRM-85] MDL Hello World: First Live Shader in Omniverse

**Status**: рџ”„ In Progress | **Priority**: Medium | **Estimate**: 2h
**Objective**: Goal: author the simplest possible MDL material by hand and
  attach it to an object in Omniverse, confirming it renders without errors.
  Acceptance Criteria: - Create a minimal .mdl file (mdl 1.7, import ::base)
  that returns a solid red diffuse colour via OmniPBR or a raw material
  construct. - Save the file inside the project at src/mdl/hello_world.mdl. -
  Reference the .mdl from a USD stage (either via UsdShade or Omniverse
  Materials panel) and confirm the object renders red in RTX Path Tracing and
  RTX Real-Time. - Document in docs/knowledge_base/mdl/ the exact steps taken:
  file location, how to assign material in Omniverse, known gotchas.  Estimated
  effort: 2 hours. Blocks all subsequent MDL tasks.

### вЏёпёЏ [KRM-86] MDL State Functions: Diagnostic Shaders for Geometry Inspection

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 3h
**Objective**: Goal: understand and document which MDL state:: functions are
  available in Omniverse and what coordinate space/conventions they operate in.
  Acceptance Criteria: - Write a set of simple diagnostic .mdl materials (e.g.
  normal_as_colour.mdl, position_as_colour.mdl, direction_as_colour.mdl) that
  visualise state::normal(), state::position(), state::direction(),
  state::texture_coordinate(0). - Confirm results visually in Omniverse on a UV-
  mapped mesh exported from Houdini. - Document findings: which functions are
  available, what space they return data in (object / world / tangent), and any
  differences between RTX modes. - Pay particular attention to
  state::direction() вЂ” this is the camera view vector needed for the parallax
  ray-marching step.  Estimated effort: 3 hours. Required before writing any PIM
  mathematics.

### вЏёпёЏ [KRM-87] MDL Primvar Access: Reading roomP, tangentu, tangentv in Omniverse

**Status**: вЏёпёЏ To Do | **Priority**: Medium | **Estimate**: 4h
**Objective**: Goal: confirm and document the exact mechanism for reading named
  USD primvars (roomP, tangentu, tangentv) inside an MDL shader running in
  Omniverse.  Background: the Room Map Frame SOP outputs three Vertex-rate
  primvars. Our PIM shader depends entirely on these. If MDL cannot read them
  natively, we must identify the fallback (e.g. baking to UV channels or using
  OmniGraph).  Acceptance Criteria: - Research MDL primvar access:
  state::texture_coordinate(N) for UV-mapped channels vs. any named-primvar API
  available in Omniverse extensions. - Export a test USD from Houdini that
  contains roomP / tangentu / tangentv as vertex primvars on a simple quad. -
  Write a diagnostic MDL that reads one of these primvars and outputs it as
  colour; verify the correct data is visible in Omniverse. - Document the
  confirmed access pattern (or the confirmed workaround) in
  docs/knowledge_base/mdl/primvar_access.md. This document becomes the technical
  contract for KRM-63 (PIM shader implementation).  Estimated effort: 4 hours.
  This is the critical blocker for the full shader.

---

## рџ§© EPIC: MDL Shader Implementation (KRM-63)

**Status**: вЏёпёЏ To Do | **Priority**: Medium

---

## рџ§© EPIC: Performance Optimisation (KRM-64)

**Status**: вЏёпёЏ To Do | **Priority**: Medium

---

## рџ§© EPIC: Testing & Integration (KRM-65)

**Status**: вЏёпёЏ To Do | **Priority**: Medium

---

## рџ“Љ Progress Summary

| Epic | Status | Priority | Completion |
| --- | --- | --- | --- |
| Text | вњ… Done | Medium | 100% (3/3) |
| VO | вњ… Done | Medium | 100% (5/5) |
| Tutorial: Shots | вЏёпёЏ To Do | Medium | 0% (0/46) |
| Analyse Karma Room Map Shader | Review | Medium | 100% (6/6) |
| MDL API & Mathematics Research | рџ”„ In Progress | Medium | 0% (0/3) |
| MDL Shader Implementation | вЏёпёЏ To Do | Medium | 0% (0/0) |
| Performance Optimisation | вЏёпёЏ To Do | Medium | 0% (0/0) |
| Testing & Integration | вЏёпёЏ To Do | Medium | 0% (0/0) |

---

## рџЋЇ Next Priorities

1. **KRM-15**: Shot 01 Intro (Priority: Medium)
2. **KRM-16**: Shot 02 Cityscapes Need Life (Priority: Medium)
3. **KRM-17**: Shot 03 Introducing the Procedural Pipeline (Priority: Medium)
4. **KRM-18**: Shot 04 Karma Room Map Shader Intro (Priority: Medium)
5. **KRM-19**: Shot 05 Need for Large Map Library (Priority: Medium)
