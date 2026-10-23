# Local PDF renderer

`pdfjs/` contains Mozilla PDF.js **6.4.299**, obtained from the official `pdfjs-dist` npm package. The package and font licenses are included beside their files. Only the minified legacy renderer and worker, character maps, standard fonts and image decoding assets are retained. PDF scripting is not enabled.

The app loads these assets from localhost; it does not contact a CDN or send PDF contents to another preview service. `pdf-preview.js` disables dynamic evaluation, WebAssembly and browser font injection to work with the application's restrictive content security policy.

Source: https://github.com/mozilla/pdf.js
