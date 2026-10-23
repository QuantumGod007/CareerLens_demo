// Mozilla PDF.js, hosted entirely by the local app. No CDN or document uploads.
import {getDocument, GlobalWorkerOptions} from '/static/vendor/pdfjs/pdf.min.mjs';
GlobalWorkerOptions.workerSrc = '/static/vendor/pdfjs/pdf.worker.min.mjs';

let task=null,documentProxy=null,renderTask=null,generation=0,pageNumber=1,rendering=false;

export function closePreview() {
  generation++;
  renderTask?.cancel();renderTask=null;
  task?.destroy();task=null;documentProxy=null;
}

export async function openPreview(url) {
  closePreview();
  const token=generation;
  const stage=document.querySelector('#pdf-stage');
  if(!stage)return;
  stage.innerHTML='<div class="pdf-loading" role="status"><span class="spinner"></span>Rendering your PDF…</div>';
  try {
    task=getDocument({url,cMapUrl:'/static/vendor/pdfjs/cmaps/',cMapPacked:true,
      standardFontDataUrl:'/static/vendor/pdfjs/standard_fonts/',wasmUrl:'/static/vendor/pdfjs/wasm/',
      isEvalSupported:false,useWasm:false,disableFontFace:true});
    documentProxy=await task.promise;
    if(token!==generation)return;
    pageNumber=1;
    document.querySelector('#pdf-prev').onclick=()=>changePage(-1);
    document.querySelector('#pdf-next').onclick=()=>changePage(1);
    await renderPage(token);
  } catch(e) {
    if(token!==generation)return;
    stage.innerHTML='<div class="pdf-loading" role="alert">The preview could not be rendered. Use Download PDF to open the actual file.</div>';
  }
}

async function changePage(delta) {
  if(rendering||!documentProxy)return;
  const next=pageNumber+delta;
  if(next<1||next>documentProxy.numPages)return;
  pageNumber=next;await renderPage(generation);
}

async function renderPage(token) {
  rendering=true;
  const stage=document.querySelector('#pdf-stage');
  try {
    const page=await documentProxy.getPage(pageNumber);
    if(token!==generation)return;
    const natural=page.getViewport({scale:1});
    const width=Math.max(220,Math.min(850,stage.clientWidth-38));
    const viewport=page.getViewport({scale:width/natural.width});
    const outputScale=Math.min(window.devicePixelRatio||1,2);
    const canvas=document.createElement('canvas');
    canvas.className='pdf-page';canvas.setAttribute('role','img');
    canvas.setAttribute('aria-label',`Actual PDF, page ${pageNumber} of ${documentProxy.numPages}. The text version is available in Resume comparison.`);
    canvas.width=Math.floor(viewport.width*outputScale);canvas.height=Math.floor(viewport.height*outputScale);
    canvas.style.width=`${Math.floor(viewport.width)}px`;canvas.style.height=`${Math.floor(viewport.height)}px`;
    renderTask=page.render({canvasContext:canvas.getContext('2d'),viewport,
      transform:outputScale!==1?[outputScale,0,0,outputScale,0,0]:null});
    await renderTask.promise;
    if(token!==generation)return;
    stage.replaceChildren(canvas);stage.scrollTop=0;
    document.querySelector('#pdf-pages').textContent=`Page ${pageNumber} of ${documentProxy.numPages}`;
    document.querySelector('#pdf-prev').disabled=pageNumber===1;
    document.querySelector('#pdf-next').disabled=pageNumber===documentProxy.numPages;
  } finally {rendering=false;}
}
