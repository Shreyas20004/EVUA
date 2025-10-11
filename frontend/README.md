## Frontend Folder Structure

This directory contains the source code for the frontend of the EVUA project. Below is an overview of the folder structure and instructions for adding new files.

### Folder Structure

```
frontend/
	public/           # Static assets (e.g., images, icons)
	src/
		components/     # Reusable React components
		pages/          # Page-level React components (route targets)
		services/       # API calls and service logic
		styles/         # CSS/SCSS files for styling
		utils/          # Utility/helper functions
		App.jsx         # Main App component
		main.jsx        # Entry point
		...             # Other source files
	index.html        # Main HTML file
	package.json      # Project dependencies and scripts
	vite.config.js    # Vite configuration
	eslint.config.js  # ESLint configuration
```

### Adding Files

- **components/**: Add new React components here. Each component should be in its own file (e.g., `MyComponent.jsx`).
- **pages/**: Add new page components here, typically one per route (e.g., `HomePage.jsx`).
- **services/**: Add files for API calls or business logic (e.g., `api.js`).
- **styles/**: Add CSS or SCSS files for styling components or pages.
- **utils/**: Add utility/helper functions used across the app.

> **Note:**
> Each folder contains a `placeholder.jsx` file to ensure the folder is tracked by version control. **Remove the placeholder file** when you add your first real file to that folder.

---
For any questions, refer to the main project README or contact the maintainers.
