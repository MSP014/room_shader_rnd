# R&D: Parallax Interior Mapping (MDL)

## 🎯 **Objective**

To engineer a custom **NVIDIA MDL (Material Definition Language)** shader that replicates the advanced logic of the **Houdini Karma Room Map Shader**. The goal is to simulate complex 3D interiors on flat surfaces using texture slicing and parallax mapping techniques, enabling the rendering of massive urban environments (Moskovsky Avenue) at 60 FPS without the geometry overhead of real interiors.

## 🔬 **Research Core**

This project is a direct port of imperative VEX code into the declarative/functional graph logic of MDL.

### **Key Features**

1. **"Fake Interior" Simulation**: using ray-box intersection logic to create the illusion of depth behind a window plane.
2. **Texture Slicing**: Implementing the specific logic of "depth slices" to simulate distinct layers within the room (e.g., curtains, furniture, back wall) rather than a simple cubemap.
3. **Procedural Variation**: Randomisation of room contents, lights, and dimensions based on `object_id` or spatial position.
4. **Optimisation**: Ensuring the shader handles thousands of concurrent instances with minimal texture lookups.

## 🛠️ **Technical Challenges**

* **Coordinate Systems**: Translating Houdini's Y-up / Z-front coordinate space to Omniverse/MDL conventions.
* **Ray-Box Intersection**: Efficiently calculating the entry and exit points of the view ray within the virtual room volume in MDL.
* **Tangent Space**: Correctly handling the tangent basis for realistic projections on deformed or rotated geometry.

## 🏆 **Strategic Context**

* **The "Technical Proof"**: This project serves as the primary evidence of **Technical Artist** competencies for the NVIDIA application. It demonstrates the ability not just to *use* the platform, but to *extend* it.
* **Community Contribution**: The final asset is intended for release to the Omniverse community (Discord/Gumroad), positioning the author as a contributor and tool-builder.

## 🔗 **Relation to Case 01**

This shader is the critical visual component for **Case 01 - Moskovsky Av**. It will be applied to the thousands of windows in the "Electrosila" factory and surrounding residential blocks to bring the city to life.
