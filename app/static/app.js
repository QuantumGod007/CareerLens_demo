'use strict';

const paths = {
  layout:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  search:'<circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 4.5 4.5"/>',
  file:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h6"/>',
  history:'<path d="M3 11a9 9 0 1 1 2.6 7.4M3 4v7h7M12 7v5l3 2"/>',
  upload:'<path d="M12 16V3m-5 5 5-5 5 5M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5"/>',
  arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  back:'<path d="M20 12H4m6-6-6 6 6 6"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  checkCircle:'<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  circle:'<circle cx="12" cy="12" r="8"/>',
  location:'<path d="M20 10c0 6-8 11-8 11S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
  briefcase:'<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v3M3 12a22 22 0 0 0 18 0M12 12v3"/>',
  shield:'<path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
  focus:'<path d="M8 3H5a2 2 0 0 0-2 2v3m13-5h3a2 2 0 0 1 2 2v3M3 16v3a2 2 0 0 0 2 2h3m8 0h3a2 2 0 0 0 2-2v-3"/><circle cx="12" cy="12" r="3"/>',
  layers:'<path d="m12 3 10 5-10 5L2 8Zm-9 9 9 5 9-5M3 16l9 5 9-5"/>',
  edit:'<path d="m16 3 5 5-12 12-6 1 1-6Z M13 6l5 5"/>',
  external:'<path d="M14 3h7v7m0-7L10 14M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/>',
  download:'<path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4"/>',
  close:'<path d="m6 6 12 12M6 18 18 6"/>',
  menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  mail:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 6 9 7 9-7"/>',
  eye:'<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
  send:'<path d="m22 2-7 20-4-9-9-4 20-7ZM22 2 11 13"/>',
};
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.file}</svg>`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeURL = value => {try {const url=new URL(value);return url.protocol==='https:'?esc(url.href):'#';}catch{return '#';}};
const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const main = $('#main'), modal = $('#modal');
const sections = ['summary','education','experience','projects','certifications','achievements'];
const sectionName = s => s.charAt(0).toUpperCase()+s.slice(1);
const fmtDate = value => new Intl.DateTimeFormat(undefined,{day:'numeric',month:'short',year:'numeric'}).format(new Date(value));
const timeAgo = value => {const hrs=Math.floor((Date.now()-new Date(value))/3600000);return hrs<1?'Just now':hrs<24?`${hrs}h ago`:fmtDate(value);};
const initials = name => name.split(/\s+/).filter(Boolean).slice(0,2).map(s=>s[0]).join('').toUpperCase() || 'Y';
const percent = score => score?.percentage == null ? 'N/A' : `${Number(score.percentage).toFixed(score.percentage%1 ? 1:0)}%`;
const tag = (text, type='') => `<span class="skill-tag ${type}">${esc(text)}</span>`;
const badge = (text, type='') => `<span class="badge ${type?'badge-'+type:''}">${esc(text)}</span>`;
const state = {candidate:null,history:[],jobs:[],sources:[],fetched:null,fetchedCount:0,selected:null,record:null,
  tab:'analysis',editing:false,busy:null,error:'',selectedFile:null,uploading:false,configured:false,model:'',scoringVersion:1,
  filters:{role:'Software Developer Intern',location:'',entry_only:false},records:new Map(),receipt:null};

function hydrateIcons(root=document) {$$('[data-icon]',root).forEach(el=>el.innerHTML=icon(el.dataset.icon));}
hydrateIcons();

async function api(path, options={}) {
  const controller = new AbortController();
  const timeout = setTimeout(()=>controller.abort(), 240000);
  try {
    const isForm=options.body instanceof FormData;
    const response = await fetch(path,{...options,headers:{...(isForm?{}:{'Content-Type':'application/json'}),...options.headers},signal:controller.signal});
    const data=await response.json().catch(()=>({detail:'The server returned an unreadable response.'}));
    if(!response.ok) {
      let message=data.detail;
      if(Array.isArray(message)) message=message.map(x=>x.msg).join(' ');
      throw new Error(message || `Request failed (${response.status}).`);
    }
    return data;
  } catch(e) {
    if(e.name==='AbortError') throw new Error('This operation took too long. Check your connection and try again.');
    if(e instanceof TypeError) throw new Error('The local server is unreachable. Check that CareerLens is running.');
    throw e;
  } finally {clearTimeout(timeout);}
}

let toastTimer;
function toast(message, error=false) {
  clearTimeout(toastTimer);
  $('#toast-region').innerHTML=`<div class="toast ${error?'error':''}">${icon(error?'info':'checkCircle')}<span>${esc(message)}</span><button class="icon-button" data-action="dismiss-toast" aria-label="Dismiss notification">${icon('close')}</button></div>`;
  toastTimer=setTimeout(()=>$('#toast-region').innerHTML='',error?14000:6500);
}
function notice(message,type='') {return `<div class="inline-notice ${type}" role="${type==='error'?'alert':'note'}">${icon('info')}<span>${esc(message)}</span></div>`;}
function empty(iconName,title,description,action,label) {return `<div class="empty-state"><div class="empty-icon">${icon(iconName)}</div><h2>${esc(title)}</h2><p>${esc(description)}</p>${action?`<button class="button button-primary" data-action="${action}">${icon(action==='upload'?'upload':'search')}${esc(label)}</button>`:''}</div>`;}
function titleBlock(kicker,title,description,actions='') {return `<div class="page-heading"><div><div class="eyebrow">${esc(kicker)}</div><h1>${esc(title)}</h1><p>${esc(description)}</p></div>${actions}</div>`;}
function isBusy(){return !!state.busy;}
function loading(title, description, steps=[]) {return `<div class="loading-panel" role="status"><span class="spinner spinner-large"></span><h2>${esc(title)}</h2><p>${esc(description)}</p>${steps.length?`<div class="loading-steps">${steps.map((s,i)=>`<span>${icon(['file','focus','shield'][i%3])}${esc(s)}</span>`).join('')}</div>`:''}</div>`;}

function setSidebar() {
  const name=state.candidate?.profile.name;
  $('#sidebar-name').textContent=name||'Your workspace';$('#avatar').textContent=initials(name||'Your workspace');
  $('#connection').innerHTML=`<span class="live-dot"></span>${state.configured?'Gemini configured':'Key needed'}`;
  $('#connection').title=state.configured?`API key configured · ${state.model}. Connectivity is checked when requests run.`:'Set GEMINI_API_KEY in .env';
  const count=$('#job-count');count.hidden=!state.jobs.length;count.textContent=state.jobs.length;
}
function updateSidebarAccess(){const hidden=window.matchMedia('(max-width:760px)').matches&&!$('#sidebar').classList.contains('open');$('#sidebar').inert=hidden;$('#sidebar').setAttribute('aria-hidden',String(hidden));}
window.addEventListener('resize',updateSidebarAccess);
updateSidebarAccess();
function currentRoute(){return (location.hash.slice(1)||'overview').split('/')[0];}
function go(route){if(location.hash===`#${route}`)render();else location.hash=route;}

function render() {
  const route=currentRoute();
  $$('[data-nav]').forEach(el=>{const active=el.dataset.nav===(route==='assessment'?'jobs':route);el.classList.toggle('active',active);if(active)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});
  $('#page-title').textContent=({overview:'Overview',jobs:'Find jobs',resume:'My resume',history:'Application history',assessment:'Role workspace'})[route]||'Overview';
  setSidebar();
  main.innerHTML=({overview:renderOverview,jobs:renderJobs,resume:renderResume,history:renderHistory,assessment:renderAssessment})[route]?.()||renderOverview();
  $$('[data-progress]',main).forEach(el=>el.style.width=`${Math.max(0,Math.min(100,Number(el.dataset.progress)||0))}%`);
  hydrateIcons(main);
}

function renderOverview() {
  const c=state.candidate,p=c?.profile;
  const prepared=state.history.length,simulations=state.history.reduce((n,r)=>n+(r.simulations?.length||0),0);
  const firstName=p?.name.split(' ')[0];
  return `${titleBlock('YOUR WORKSPACE',firstName?`Welcome back, ${firstName}.`:'Your next move, in focus.','Your experience, opportunities and saved assessments, in one place.',`<span class="date-label">${fmtDate(new Date())}</span>`)}
  ${!state.configured?notice('Add your Gemini API key to .env to enable resume extraction and tailoring.','warning'):''}
  <section class="welcome-panel"><div class="welcome-copy"><div class="eyebrow">YOUR NEXT STEP</div><h2>${p?'Find the role worth preparing for.':'Start with your experience.'}</h2><p>${p?`Discover published opportunities for <strong>${esc(c.preferred_role)}</strong>, then prepare a resume grounded in your saved profile.`:'Upload your resume, review the extracted details, and discover real roles that connect with your skills.'}</p><div class="welcome-actions"><button class="button button-primary" data-action="${p?'find-jobs':'upload'}">${icon(p?'search':'upload')}${p?'Find matching roles':'Upload your resume'}${icon('arrow')}</button><small>${p?'Live company boards · Your actual skills':'PDF · Up to 10 MB · 15 pages'}</small></div></div>
  <div class="step-strip"><div class="step-item ${p?'done':'current'}"><span class="step-number">${p?icon('check'):'01'}</span><div><strong>${p?'Profile saved':'Upload & review'}</strong><small>Your original experience</small></div></div><div class="step-item ${p?'current':''}"><span class="step-number">02</span><div><strong>Discover roles</strong><small>Published employer listings</small></div></div><div class="step-item ${prepared?'done':''}"><span class="step-number">${prepared?icon('check'):'03'}</span><div><strong>Enhance & compare</strong><small>Save a version for each role</small></div></div></div></section>
  <section class="stats" aria-label="Workspace statistics"><div class="stat"><div class="stat-top">${icon('layers')}Skills in your profile</div><strong>${p?.skills.length||0}</strong><small>${p?'From your saved resume':'Upload to build your profile'}</small></div><div class="stat"><div class="stat-top">${icon('file')}Resumes prepared</div><strong>${prepared}</strong><small>Saved role-specific versions</small></div><div class="stat"><div class="stat-top">${icon('send')}Local simulations</div><strong>${simulations}</strong><small>Test submissions only</small></div></section>
  <div class="overview-grid"><section><div class="section-header"><h2>Recent activity</h2>${prepared?'<a class="button-link" href="#history">View all '+icon('arrow')+'</a>':''}</div>${prepared?`<div class="recent-list">${state.history.slice(0,4).map(r=>`<div class="recent-item"><div class="company-logo">${esc(initials(r.job.company))}</div><div><h3>${esc(r.job.title)}</h3><p>${esc(r.job.company)} · Resume prepared · ${timeAgo(r.created_at)}</p></div><button class="button-link" data-action="open-record" data-id="${r.id}">Open ${icon('arrow')}</button></div>`).join('')}</div>`:`<div class="activity-empty">${icon('history')}<div><strong>No assessments yet.</strong><p>Once you prepare a resume for a role, its assessment and PDF will appear here.</p></div></div>`}</section>
  <aside class="overview-aside">${p?`<section class="panel profile-snapshot"><div class="eyebrow">YOUR SAVED PROFILE</div><div class="snapshot-name"><span class="avatar">${esc(initials(p.name))}</span><h3>${esc(p.name||'Your saved profile')}</h3></div>${badge(c.confirmed?'Profile confirmed':'Review profile',c.confirmed?'green':'amber')}<p>${esc(c.preferred_role)}</p><div class="tag-list">${p.skills.slice(0,8).map(x=>tag(x)).join('')}${p.skills.length>8?tag(`+${p.skills.length-8} more`):''}</div><div class="profile-snapshot-footer"><small>Updated ${fmtDate(c.updated_at)}</small><a class="button-link" href="#resume">View resume ${icon('arrow')}</a></div></section>`:`<section class="panel upload-panel"><div class="dropzone" data-drop="quick" role="button" tabindex="0" aria-label="Upload your PDF resume"><div class="upload-symbol">${icon('upload')}</div><h3>Your resume starts here.</h3><p>Drop a PDF or choose one from your device.</p><button class="button button-secondary" data-action="upload">${icon('file')}Choose a PDF</button><small>PDF only · Up to 10 MB · 15 pages</small></div><div class="panel-footnote">${icon('shield')}Saved locally. Sent to Gemini when processing.</div></section>`}
  <section class="insight-panel"><h3>What goes into a match?</h3><p>Published job requirements are compared with evidence in your resume. Coverage measures explicit required skills; it is not an employer ATS score.</p><div class="insight-row">${icon('shield')}<div><h4>Your facts stay the source.</h4><p>Review every change before using a generated resume.</p></div></div></section></aside></div>`;
}

function renderJobs() {
  const heading=titleBlock('OPPORTUNITIES','Find your next role.','Live company listings, matched to the skills in your resume.');
  if(!state.candidate) return heading+empty('search','Start with your resume.','Upload your resume so we can connect live job listings with your actual skills and preferred role.','upload','Upload your resume');
  if(!state.candidate.confirmed)return heading+empty('checkCircle','Review your extracted profile first.','Confirm the details before matching jobs or enhancing your resume.','review-profile','Review profile');
  const search=`<form id="search-form" class="search-bar"><div class="input-wrap">${icon('search')}<label class="sr-only" for="role-search">Preferred role</label><input id="role-search" name="role" required minlength="2" maxlength="150" value="${esc(state.filters.role)}" placeholder="e.g. Software Developer Intern"></div><div class="input-wrap location-input">${icon('location')}<label class="sr-only" for="location-search">Location filter</label><input id="location-search" name="location" maxlength="150" value="${esc(state.filters.location)}" placeholder="Location or remote"></div><button class="button button-primary" type="submit" ${isBusy()?'disabled':''}>${state.busy==='discover'?'<span class="spinner"></span>':icon('search')}Find roles</button><label class="check-label"><input type="checkbox" name="entry_only" ${state.filters.entry_only?'checked':''}>Early-career titles only</label></form>`;
  const profilebar=`<div class="profile-info-bar"><span>Matching with <strong>${esc(state.candidate.profile.name||'your saved profile')}</strong> · ${state.candidate.profile.skills.length} saved skills</span><button class="button-link" data-action="edit-profile">Edit profile ${icon('arrow')}</button></div>`;
  if(state.busy==='analyse')return heading+loading('Analysing this role.','Gemini is checking the role, tailoring your saved facts, and verifying the wording. This can take a minute or two.',['Read the requirements','Tailor your experience','Verify & generate PDF']);
  if(state.busy==='discover')return heading+search+loading('Finding published opportunities.','Fetching published listings from your configured company boards. Every result comes from a public career source.',['Fetch live roles','Compare your skills','Rank relevant titles']);
  const error=state.error?notice(state.error,'error'):'';
  if(!state.fetched)return heading+search+profilebar+error+empty('briefcase','Search the company boards.','Search your preferred role to fetch live jobs. You can adjust the company boards in your local .env file.','find-jobs','Find matching roles');
  const statuses=`<div class="source-status">${state.sources.map(s=>`<span class="source-item ${s.ok?'':'failed'}" title="${esc(s.message)}"><span class="live-dot"></span>${esc(s.board)} · ${s.ok?`${s.count} live roles`:'unavailable'}</span>`).join('')}${!state.sources.length?'No sources configured. Add GREENHOUSE_BOARDS or LEVER_BOARDS to .env and restart.':''}</div>`;
  const toolbar=`<div class="results-toolbar"><strong>${state.jobs.length} relevant ${state.jobs.length===1?'role':'roles'}</strong><small>${state.fetchedCount} listings checked · Fetched ${timeAgo(state.fetched)}</small></div>`;
  if(!state.jobs.length)return heading+search+profilebar+error+toolbar+statuses+empty('search','No roles match these filters.','No listings matched these filters. Try a broader role title, remove the location filter, or change your configured company boards.');
  const selected=state.jobs.find(j=>j.id===state.selected)||state.jobs[0];
  return heading+search+profilebar+error+toolbar+statuses+`<div class="job-layout"><div class="job-list" role="list" aria-label="Matching jobs">${state.jobs.map(job=>`<div role="listitem"><button class="job-card ${job.id===selected.id?'selected':''}" data-action="select-job" data-id="${esc(job.id)}" aria-pressed="${job.id===selected.id}"><div class="job-card-head"><span class="company-logo">${esc(initials(job.company))}</span><div><div class="company-name">${esc(job.company)}</div><div class="job-source">${esc(sectionName(job.source))} · Public career board</div></div></div><h3>${esc(job.title)}</h3><div class="job-meta"><span>${icon('location')}${esc(job.location)}</span>${job.job_type?`<span>${icon('briefcase')}${esc(job.job_type)}</span>`:''}</div><div class="tag-list">${job.matched_skills.slice(0,4).map(s=>tag(s)).join('')}</div><div class="job-match">${icon('focus')}${job.matched_skills.length?`${job.matched_skills.length} of your skills ${job.matched_skills.length===1?'appears':'appear'} in this role`:'Title matches your search'}</div></button></div>`).join('')}</div><section class="panel job-detail" aria-label="Selected job details">${jobDetail(selected)}</section></div>`;
}

function jobDescription(text) {
  return text.split('\n').map(line=>{
    if(!line.trim())return '';
    const heading=line.length<85&&/^(?:about (?:us|the (?:role|team|company))|(?:key )?responsibilities|(?:minimum |preferred )?(?:qualifications|requirements)|what you(?:’|')ll (?:do|bring)|who you are|benefits|bonus points|available locations|desirable skills)/i.test(line.trim());
    return heading?`<h4 class="jd-heading">${esc(line)}</h4>`:`<p>${esc(line)}</p>`;
  }).join('');
}
function jobDetail(job) {return `<div class="detail-header"><div class="detail-company"><div class="company-logo">${esc(initials(job.company))}</div><div><div class="company-name">${esc(job.company)}</div><small class="job-source">Published on ${esc(sectionName(job.source))}</small></div></div><h2>${esc(job.title)}</h2><div class="job-meta"><span>${icon('location')}${esc(job.location)}</span>${job.job_type?`<span>${icon('briefcase')}${esc(job.job_type)}</span>`:''}</div><div class="detail-actions"><button class="button button-primary" data-action="analyse-job" data-id="${esc(job.id)}" ${isBusy()?'disabled':''}>${icon('focus')}Analyse & enhance${icon('arrow')}</button><a class="button button-secondary" href="${safeURL(job.url)}" target="_blank" rel="noopener noreferrer">View listing${icon('external')}</a></div></div><div class="detail-match-note"><strong>Why this role?</strong> ${esc(job.match_reasons.join(' · '))}.<br>Skill mentions help with discovery; required-skill coverage is assessed separately.</div><div class="detail-body"><h3>About the opportunity</h3><div class="job-description">${jobDescription(job.description||'This source did not provide a description. Open the employer listing for details.')}</div></div>`;}

function profileFact(fact) {
  let lines=fact.text.split('\n').map(line=>line.trim()).filter(Boolean);
  if(lines.length===1&&['projects','experience'].includes(fact.section)){
    const split=lines[0].indexOf(': ');
    if(split>0&&split<160&&!/^(?:built|developed|created|used|designed|implemented|worked)\b/i.test(lines[0]))lines=[lines[0].slice(0,split),lines[0].slice(split+2)];
  }
  const grouped=lines.length>1&&['education','experience','projects'].includes(fact.section);
  if(!grouped)return `<section class="resume-entry"><p>${esc(fact.text)}</p></section>`;
  return `<section class="resume-entry"><h4>${esc(lines[0])}</h4><ul>${lines.slice(1).map(line=>`<li>${esc(line.replace(/^[-•*]\s+/,''))}</li>`).join('')}</ul></section>`;
}
function profileDocument(profile, order=sections, diffMap=null, original=false) {
  return `<div class="profile-document-head"><h2>${esc(profile.name||'Your resume')}</h2><div class="contact-line">${[profile.email,profile.phone,profile.location].filter(Boolean).map(esc).join(' · ')}${profile.links.length?'<br>'+profile.links.map(esc).join('<br>'):''}</div></div>${profile.skills.length?`<section class="resume-section"><h3>Skills</h3><div class="tag-list">${profile.skills.map(x=>tag(x)).join('')}</div></section>`:''}${[...new Set([...order,...sections])].map(section=>{const facts=profile.facts.filter(f=>f.section===section);return !facts.length?'':`<section class="resume-section"><h3>${sectionName(section)}</h3>${facts.map(f=>diffMap?`<div class="fact-text">${diffMap[f.id]?.[original?'before':'after']||esc(f.text)}</div>`:profileFact(f)).join('')}</section>`;}).join('')}`;
}

function renderResume() {
  const c=state.candidate;
  if(!c)return titleBlock('YOUR EXPERIENCE','Your resume workspace.','Start with your original PDF and review the extracted profile.')+empty('file','No resume uploaded yet.','Upload a PDF resume. Gemini will extract your skills, education, projects and experience into an editable profile.','upload','Upload your resume');
  const heading=titleBlock('YOUR EXPERIENCE','Your resume workspace.','Review your saved profile. This is the source for every role-specific resume.',`<div class="responsive-actions"><button class="button button-secondary" data-action="preview-original">${icon('eye')}Original PDF</button><button class="button button-primary" data-action="${state.editing?'cancel-edit':'edit-profile'}">${icon(state.editing?'close':'edit')}${state.editing?'Cancel':'Edit profile'}</button></div>`);
  if(state.editing) return heading+`<form id="profile-form" class="panel edit-form"><div class="section-header"><h2>Edit your saved profile</h2>${badge('Your edits become the source of truth','blue')}</div>${notice('Only add information that is true. Future tailoring uses this profile; earlier saved assessments keep their original snapshots.')}<div class="form-grid"><label>Full name<input name="name" maxlength="200" value="${esc(c.profile.name)}"></label><label>Preferred role<input name="preferred_role" required minlength="2" maxlength="150" value="${esc(c.preferred_role)}"></label><label>Email<input name="email" type="email" value="${esc(c.profile.email)}"></label><label>Phone<input name="phone" maxlength="100" value="${esc(c.profile.phone)}"></label><label>Location<input name="location" maxlength="300" value="${esc(c.profile.location)}"></label><label>Links <span class="optional">one per line</span><textarea name="links" rows="2">${esc(c.profile.links.join('\n'))}</textarea></label><label class="full">Skills <span class="optional">separate with commas</span><textarea name="skills" rows="2">${esc(c.profile.skills.join(', '))}</textarea></label></div>${sections.map(s=>`<section class="edit-section"><h3>${sectionName(s)}</h3><p>Separate facts with a blank line. Keep titles, dates and supporting details together.</p><label class="sr-only" for="edit-${s}">${sectionName(s)} facts</label><textarea name="${s}" id="edit-${s}" rows="5">${esc(c.profile.facts.filter(f=>f.section===s).map(f=>f.text).join('\n\n'))}</textarea></section>`).join('')}<div id="profile-error"></div><div class="form-actions"><button class="button button-primary" type="submit" ${isBusy()?'disabled':''}>${icon('check')}Save profile</button><button class="button button-secondary" type="button" data-action="cancel-edit">Cancel</button></div><p class="form-saved-note">Your original uploaded PDF stays available. Profile edits apply to future tailored versions.</p></form>`;
  const confirmation=c.confirmed?notice('Profile confirmed. You can find jobs and enhance your resume.'):`<div class="profile-info-bar"><span>Review the extracted details below. Edit anything Gemini missed, then confirm this profile.</span><button class="button button-primary" data-action="confirm-profile" ${isBusy()?'disabled':''}>${icon('check')}Confirm profile & find jobs</button></div>`;
  return heading+confirmation+`<div class="profile-layout"><article class="panel profile-document">${profileDocument(c.profile)}</article><aside class="resume-side"><section class="panel"><div class="eyebrow">PROFILE STATUS</div><div class="profile-verified">${icon('checkCircle')}Extracted & saved locally</div><p>${c.profile.skills.length} skills · ${c.profile.facts.length} facts<br>Updated ${fmtDate(c.updated_at)}</p><button class="button button-secondary" data-action="preview-original">${icon('eye')}View original PDF</button></section><section class="panel"><h3>Your preferred direction</h3><p>${esc(c.preferred_role)}</p><button class="button button-primary" data-action="find-jobs">${icon('search')}Find matching roles</button></section><section class="panel"><h3>A profile you can trust</h3><p>Review the extracted details and correct anything Gemini missed. Tailoring uses your saved facts, with an independent check on rewritten claims.</p><button class="button button-quiet" data-action="upload">${icon('upload')}Replace original resume</button></section></aside></div>`;
}

function renderHistory() {
  const heading=titleBlock('SAVED WORK','Your application history.','Every prepared resume, linked to its role, assessment and original profile.');
  if(!state.history.length)return heading+empty('history','No saved assessments yet.','Prepared resumes and local test submissions will appear here. Each assessment is saved separately, so your earlier versions stay available.',state.candidate?'find-jobs':'upload',state.candidate?'Discover roles':'Upload your resume');
  return heading+`<div class="table-wrap" tabindex="0" role="region" aria-label="Saved assessments"><table><thead><tr><th>Role & company</th><th>Skill coverage</th><th>Status</th><th>Prepared</th><th>Actions</th></tr></thead><tbody>${state.history.map(r=>`<tr><td><span class="table-role">${esc(r.job.title)}</span><span class="table-company">${esc(r.job.company)} · ${esc(r.job.location)}</span></td><td><span class="coverage-number">${percent(r.tailored_score)}<small>${r.tailored_score.matched_count} / ${r.tailored_score.total} required skills</small></span></td><td>${r.simulations?.length?badge('Simulated','amber'):badge('Prepared','blue')}</td><td>${fmtDate(r.created_at)}</td><td><div class="table-actions"><button class="button-link" data-action="open-record" data-id="${r.id}">Open${icon('arrow')}</button><a class="button-link" href="/api/history/${r.id}/pdf" aria-label="Download resume for ${esc(r.job.title)}">${icon('download')}</a></div></td></tr>`).join('')}</tbody></table></div><p class="history-note">Coverage is a local required-skill check, not an employer ATS score. “Simulated” means a local test receiver only.</p>`;
}

function renderAssessment() {
  if(state.busy==='analyse')return loading('Analysing this role.','Analysing requirements, tailoring your saved experience, and checking every rewritten claim. This can take a minute or two.',['Read the requirements','Tailor your experience','Verify & generate PDF']);
  const r=state.record;
  if(!r)return empty('file','Open a saved role.','Choose a role from your application history or analyse a published job to open its workspace.','view-history','View application history');
  const tabs=[['analysis','Role analysis'],['comparison','Resume comparison'],['coverage','Skill coverage'],['review','Review application']];
  return `<button class="button-link back-link" data-action="back-jobs">${icon('back')}Back to opportunities</button><div class="assessment-header"><div><div class="eyebrow">YOUR ROLE WORKSPACE ${r.simulations?.length?'· SIMULATED':'· PREPARED'}</div><h1>${esc(r.job.title)}</h1><div class="job-meta"><span>${icon('briefcase')}${esc(r.job.company)}</span><span>${icon('location')}${esc(r.job.location)}</span><span>${fmtDate(r.created_at)}</span><span>${badge(percent(r.tailored_score)+' required-skill coverage','blue')}</span></div></div><div class="assessment-actions"><button class="button button-secondary" data-action="preview-pdf">${icon('eye')}Preview PDF</button><a class="button button-primary" href="/api/history/${r.id}/pdf">${icon('download')}Download PDF</a></div></div><div class="tab-bar" role="tablist" aria-label="Assessment sections">${tabs.map(([id,label])=>`<button id="tab-${id}" role="tab" aria-controls="assessment-panel" aria-selected="${state.tab===id}" tabindex="${state.tab===id?'0':'-1'}" class="${state.tab===id?'active':''}" data-action="tab" data-tab="${id}">${label}</button>`).join('')}</div><section id="assessment-panel" role="tabpanel" aria-labelledby="tab-${state.tab}">${savedVersionNotice(r)}${({analysis:analysisView,comparison:comparisonView,coverage:coverageView,review:reviewView})[state.tab](r)}</section>`;
}

function savedVersionNotice(r) {
  if((r.scoring_version||1)>=state.scoringVersion)return '';
  return `<div class="profile-info-bar"><span>Coverage refreshed using the same requirements. Previously saved: ${percent(r.saved_scores?.original||r.original_score)} original / ${percent(r.saved_scores?.tailored||r.tailored_score)} tailored. Prepare a separate version for updated wording and typography; your existing PDF stays saved.</span><button class="button button-secondary button-small" data-action="prepare-updated" ${isBusy()?'disabled':''}>Prepare updated version ${icon('arrow')}</button></div>`;
}
function pdfFormatNote(r) {
  const style=r.pdf_style||{font:'Bitstream Vera Sans',body_pt:9.2,heading_pt:9,name_pt:22,contact_pt:8.1,page:'A4'};
  return `<p class="plain-note">PDF format: ${esc(style.font)} · ${style.body_pt} pt body · ${style.heading_pt} pt headings · ${style.name_pt} pt name · ${esc(style.page)}, single column. Gemini tailors the content; a consistent PDF template controls typography and spacing. Your original PDF is preserved.</p>`;
}
function scoreEvidence(score) {
  return (score.evidence||[]).filter(item=>item.matched).map(item=>`<details class="score-evidence"><summary>Why ${esc(item.skill)} matched</summary><p class="plain-note">${esc(item.method)}<br>“${esc(item.evidence)}”</p></details>`).join('');
}

function coveragePanel(score,title,showSkills=false) {
  return `<section class="coverage-panel"><h3>${esc(title)}</h3><div class="coverage-big">${score.percentage==null?'N/A':Number(score.percentage).toFixed(score.percentage%1?1:0)}${score.percentage==null?'':'<span>%</span>'}</div><p>${score.total?`${score.matched_count} of ${score.total} explicit required skills present`:'No explicit mandatory skills identified'}</p><div class="progress-track" role="${score.total?'progressbar':'presentation'}" ${score.total?`aria-label="${esc(title)}" aria-valuenow="${score.percentage}" aria-valuemin="0" aria-valuemax="100"`:''}><div class="progress-fill" data-progress="${score.percentage||0}"></div></div><div class="coverage-caption"><span>Required-skill coverage</span><span>${score.total?`${score.matched_count} / ${score.total}`:'N/A'}</span></div>${showSkills?`<div class="score-skills"><h4>Present in this version</h4><div class="tag-list">${score.matched.length?score.matched.map(s=>tag(s,'matched')).join(''):'<small>None identified.</small>'}</div>${scoreEvidence(score)}</div><div class="score-skills"><h4>Missing from this version</h4><div class="tag-list">${score.missing.length?score.missing.map(s=>tag(s,'missing')).join(''):`<small>${score.total?'No required-skill gaps found.':'No explicit mandatory skills to compare.'}</small>`}</div></div>`:''}<p class="coverage-disclaimer">Matched explicit required skills ÷ all explicit required skills. A local evidence check, not an employer ATS score or a prediction of shortlisting.</p></section>`;
}

function analysisView(r) {
  return `${!r.verification_available?notice('The independent wording check was unavailable. Proposed rewrites were replaced with the original facts.','warning'):''}<div class="assessment-grid"><div><section class="panel analysis-panel"><div class="section-header"><h2>Required skills</h2>${badge(`${r.analysis.required.length} explicit required skills`)}</div>${r.analysis.required.length?`<div class="requirement-list">${r.analysis.required.map(item=>{const matched=r.tailored_score.matched.includes(item.skill);return `<div class="requirement">${icon(matched?'checkCircle':'circle').replace('<svg','<svg class="'+(matched?'matched-icon':'missing-icon')+'"')}<div><strong>${esc(item.skill)}</strong><p>“${esc(item.evidence)}”</p></div>${badge(matched?'Present':'Gap',matched?'green':'amber')}</div>`;}).join('')}</div>`:'<p class="plain-note">No explicit mandatory named skills were identified in the listing. Coverage is N/A; responsibilities and other eligibility conditions still matter.</p>'}</section><section class="panel analysis-panel"><div class="section-header"><h2>Preferred skills</h2>${badge('Preferred')}</div>${r.analysis.preferred.length?`<div class="requirement-list">${r.analysis.preferred.map(item=>`<div class="requirement">${icon('layers')}<div><strong>${esc(item.skill)}</strong><p>“${esc(item.evidence)}”</p></div></div>`).join('')}</div>`:'<p class="plain-note">No separate preferred skills were identified.</p>'}</section><section class="panel analysis-panel"><div class="section-header"><h2>Responsibilities</h2></div>${r.analysis.responsibilities.length?`<ul class="bullet-list">${r.analysis.responsibilities.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class="plain-note">Open the employer listing for responsibilities.</p>'}${r.analysis.note?`<div class="gaps-box"><h4>Qualification & location notes</h4><p class="plain-note">${esc(r.analysis.note)}</p></div>`:''}</section></div><aside class="assessment-side"><div class="panel">${coveragePanel(r.tailored_score,'Your enhanced resume')}</div><div class="mini-detail"><h3>Your experience stays yours.</h3><p>The resume uses only your saved skills and facts. Missing requirements stay visible. No skills are added just to make a number go up.</p><button class="button-link" data-action="tab" data-tab="comparison">Compare the versions ${icon('arrow')}</button></div></aside></div>`;
}

// Small word-level LCS, bounded so long facts cannot stall the interface.
function diffWords(before,after) {
  if(before===after)return {before:esc(before),after:esc(after)};
  const a=before.match(/\s+|\S+/g)||[],b=after.match(/\s+|\S+/g)||[];
  if(a.length*b.length>160000)return {before:`<del>${esc(before)}</del>`,after:`<ins>${esc(after)}</ins>`};
  const dp=Array.from({length:a.length+1},()=>new Uint16Array(b.length+1));
  for(let i=a.length-1;i>=0;i--)for(let j=b.length-1;j>=0;j--)dp[i][j]=a[i]===b[j]?1+dp[i+1][j+1]:Math.max(dp[i+1][j],dp[i][j+1]);
  let i=0,j=0,left='',right='';
  while(i<a.length||j<b.length){if(i<a.length&&j<b.length&&a[i]===b[j]){left+=esc(a[i]);right+=esc(b[j]);i++;j++;}else if(j<b.length&&(i===a.length||dp[i][j+1]>=dp[i+1][j])){right+=`<ins>${esc(b[j++])}</ins>`;}else{left+=`<del>${esc(a[i++])}</del>`;}}
  return {before:left,after:right};
}

function comparisonView(r) {
  const diffs={};r.changes.filter(c=>c.kind==='wording').forEach(c=>diffs[c.source_id]=diffWords(c.before,c.after));
  return `<details class="format-details"><summary>Document format & source</summary>${pdfFormatNote(r)}</details><div class="comparison-toolbar"><p><del>Removed wording</del> &nbsp; <ins>Revised wording</ins> · Reordering is listed below.</p><button class="button button-secondary button-small" data-action="preview-original-record">${icon('eye')}Original PDF</button></div><div class="comparison-grid"><article class="comparison-column"><div class="comparison-label"><span>Original profile</span>${badge('Source facts')}</div><div class="comparison-document">${profileDocument(r.original_profile,sections,diffs,true)}</div></article><article class="comparison-column"><div class="comparison-label tailored"><span>Enhanced for this role</span>${badge(r.changes.some(c=>c.kind==='omission')?'Selected projects · see exclusions below':'All facts retained','blue')}</div><div class="comparison-document">${profileDocument(r.tailored_profile,r.section_order,diffs,false)}</div></article></div><section class="changes-section"><div class="section-header"><h2>What changed, and why</h2><small>${r.changes.filter(c=>c.kind==='wording').length} verified wording changes</small></div><div class="panel">${r.changes.length?r.changes.map(c=>`<div class="change-row">${badge(c.kind==='wording'?'Wording':c.kind==='order'?'Structure':c.kind==='omission'?'Project excluded':c.kind==='formatting'?'Formatting':'Original retained',c.kind==='wording'?'green':'')}<p>${esc(c.reason)}</p>${['wording','omission','formatting'].includes(c.kind)?`<details><summary>Show original and revised text</summary><div class="change-text"><strong>Original</strong><br>${esc(c.before)}<br><br><strong>Revised</strong><br>${esc(c.after||'Excluded from this version; preserved in the saved original profile.')}</div></details>`:c.kind==='order'?`<p>${esc(c.after)}</p>`:''}</div>`).join(''):'<div class="change-row"><p>No wording or structure changes were necessary. The PDF was regenerated using the saved facts.</p></div>'}</div></section>`;
}

function coverageView(r) {
  return notice(`Both PDFs use the same saved requirements. Original baseline: ${r.baseline}. Expand “Why matched” for supporting evidence. A clearer resume can legitimately keep the same coverage.`)+`<div class="score-comparison">${coveragePanel(r.original_score,'Original resume',true)}${coveragePanel(r.tailored_score,'Enhanced resume',true)}</div><div class="section-header"><h2>Document readability</h2><small>Separate readability checks</small></div><div class="readability-grid">${[['Original PDF',r.original_checks],['Tailored PDF',r.tailored_checks]].map(([title,checks])=>`<section class="panel checks-panel"><h3>${title}</h3>${checks.map(c=>`<div class="check-row ${c.status}">${icon(c.status==='pass'?'checkCircle':c.status==='review'?'info':'circle')}<div><strong>${esc(c.name)}</strong><p>${esc(c.detail)}</p></div></div>`).join('')}</section>`).join('')}</div><p class="history-note">Text checks can flag likely retention issues. Open both PDF previews to review visual reading order, page breaks and clipping.</p>`;
}

function reviewView(r) {
  const p=r.tailored_profile,receipt=state.receipt?.assessment_id===r.id?state.receipt:null, previous=r.simulations?.[0]?.answers||{};
  return `${receipt?`<div class="receipt" role="status"><h2>${icon('checkCircle')}Your local test is complete.</h2><p>${esc(receipt.message)} Use the employer’s original listing to submit a real application yourself.</p><small>Test receipt ${esc(receipt.id.slice(0,12))} · ${fmtDate(receipt.created_at)}</small></div>`:''}${notice('This is a simulated application using a local test receiver. These fields are local review questions; they are not a fetched employer application form. No information will be sent to an employer.','warning')}<div class="review-layout"><form id="review-form" class="panel review-form"><h2>Review your application.</h2><p>Check the attachment and fill in the missing details before running a local test.</p><div class="form-grid"><label>Full name<input name="name" required maxlength="200" value="${esc(previous.name||p.name)}" autocomplete="name"></label><label>Email address<input name="email" type="email" required maxlength="300" value="${esc(previous.email||p.email)}" autocomplete="email"></label><label class="full">Work authorization in the role’s location<input name="work_authorization" required minlength="2" maxlength="200" value="${esc(previous.work_authorization||'')}" placeholder="Describe your authorization or sponsorship needs"></label><label class="full">When could you start?<input name="availability" required minlength="2" maxlength="300" value="${esc(previous.availability||'')}" placeholder="e.g. Available from July, for a 3-month internship"></label><label class="full">Additional notes <span class="optional">optional</span><textarea name="additional_notes" maxlength="3000" rows="3" placeholder="Anything you want to include in your local review">${esc(previous.additional_notes||'')}</textarea></label></div><div class="attachment">${icon('file')}<div><strong>Your tailored resume.pdf</strong><small>Saved version for ${esc(r.job.company)}</small></div><button class="button-link" type="button" data-action="preview-pdf">Preview ${icon('external')}</button></div><label class="check-label"><input type="checkbox" name="understood" required>I understand this is a local simulation. A real application must be submitted through the employer’s website.</label><div id="review-error"></div><div class="form-actions"><button class="button button-primary" type="submit" ${isBusy()?'disabled':''}>${icon('send')}Run simulated submission</button></div></form><aside><div class="panel review-summary"><div class="eyebrow">THE OPPORTUNITY</div><h3>${esc(r.job.title)}</h3><p>${esc(r.job.company)}</p><div class="job-meta"><span>${icon('location')}${esc(r.job.location)}</span></div>${badge(r.simulations?.length?'Previously simulated':'Resume prepared',r.simulations?.length?'amber':'blue')}<div class="gaps-box"><h4>Required-skill coverage</h4><span class="coverage-number">${percent(r.tailored_score)}</span><p class="plain-note">${r.tailored_score.matched_count} of ${r.tailored_score.total} explicit required skills present.</p></div><a class="button button-secondary" href="${safeURL(r.job.url)}" target="_blank" rel="noopener noreferrer">Apply on employer website ${icon('external')}</a></div><div class="mini-detail"><h3>Before you apply</h3><p>Review the original listing for location, eligibility, required answers and deadlines. This workspace prepares your materials; you choose the next step.</p></div></aside></div>`;
}

function openUpload(file=null) {
  if(state.uploading)return;
  if(isBusy()){toast('Wait for the current operation to finish.');return;}
  state.selectedFile=null;
  modal.className='';
  $('#modal-content').innerHTML=`<div class="modal-head"><div><div class="eyebrow">YOUR ORIGINAL RESUME</div><h2 id="modal-title">Upload your resume.</h2><p>Upload your original resume and tell us where you’d like to go.</p></div><button class="icon-button" data-action="close-modal" aria-label="Close upload dialog">${icon('close')}</button></div><form id="upload-form" class="modal-body"><label>Preferred role<input id="upload-role" name="preferred_role" required minlength="2" maxlength="150" value="${esc(state.candidate?.preferred_role||state.filters.role)}" placeholder="e.g. AI/ML Intern"></label><input type="file" id="resume-file" accept="application/pdf,.pdf" class="sr-only"><div class="dropzone" data-drop="modal" role="button" tabindex="0" aria-label="Choose or drop a PDF resume"><div class="upload-symbol">${icon('upload')}</div><h3>Drop your PDF resume here</h3><p>Or choose a file from your device.</p><button type="button" class="button button-secondary" data-action="choose-file">${icon('file')}Choose a PDF</button><small>PDF · Up to 10 MB · 1–15 pages · No password</small></div><div id="selected-file"></div><div class="panel-footnote">${icon('shield')}Stored locally. Sent to Gemini for native PDF extraction.</div><div id="upload-error"></div><div id="upload-progress"></div><div class="form-actions"><button type="button" class="button button-quiet" data-action="close-modal">Cancel</button><button type="submit" class="button button-primary" id="upload-submit">Extract profile ${icon('arrow')}</button></div></form>`;
  if(!modal.open)modal.showModal();
  if(file)selectFile(file);
}
function selectFile(file) {
  if(!file)return;
  const error=$('#upload-error');
  if(!file.name.toLowerCase().endsWith('.pdf')){error.innerHTML='<div class="field-error" role="alert">Please choose a PDF resume.</div>';return;}
  if(file.size>10*1024*1024){error.innerHTML='<div class="field-error" role="alert">Choose a PDF smaller than 10 MB.</div>';return;}
  state.selectedFile=file;error.innerHTML='';
  $('#selected-file').innerHTML=`<div class="file-selected">${icon('file')}<span>${esc(file.name)}<small>${(file.size/1024).toFixed(0)} KB · Ready to extract</small></span><button class="icon-button" data-action="remove-file" type="button" aria-label="Remove selected file">${icon('close')}</button></div>`;
}
let previewModule;
async function previewPDF(url,title='Resume preview') {
  modal.className='pdf-dialog';
  const download=url.replace('inline=true','inline=false');
  $('#modal-content').innerHTML=`<div class="modal-head"><h2 id="modal-title">${esc(title)}</h2><div class="responsive-actions"><a class="button button-secondary button-small" href="${esc(download)}" download>${icon('download')}Download PDF</a><button class="icon-button" data-action="close-modal" aria-label="Close PDF preview">${icon('close')}</button></div></div><div class="pdf-toolbar"><button class="icon-button" id="pdf-prev" aria-label="Previous PDF page" disabled>${icon('back')}</button><span id="pdf-pages" aria-live="polite">Loading PDF…</span><button class="icon-button" id="pdf-next" aria-label="Next PDF page" disabled>${icon('arrow')}</button></div><div class="pdf-stage" id="pdf-stage"><div class="pdf-loading"><span class="spinner"></span>Rendering your PDF…</div></div>`;
  $('#modal-content').classList.add('pdf-content');
  if(!modal.open)modal.showModal();
  try {previewModule=await import('/static/pdf-preview.js');if(modal.open)await previewModule.openPreview(url);}
  catch {const stage=$('#pdf-stage');if(stage)stage.innerHTML='<div class="pdf-loading">The preview could not load. Use Download PDF to open the actual file.</div>';}
}

async function refresh() {
  const data=await api('/api/state');
  state.candidate=data.candidate;state.history=data.history;state.configured=data.gemini_configured;state.model=data.model;state.scoringVersion=Number(data.scoring_version)||1;
  state.history.forEach(r=>state.records.set(r.id,r));
  if(state.candidate&&!state.fetched)state.filters.role=state.candidate.preferred_role;
  setSidebar();
}

async function discoverJobs(form=null) {
  if(isBusy()||state.uploading)return;
  if(!state.candidate){openUpload();return;}
  if(!state.candidate.confirmed){go('resume');toast('Review and confirm your extracted profile first.');return;}
  if(form){const data=new FormData(form);state.filters={role:String(data.get('role')).trim(),location:String(data.get('location')).trim(),entry_only:data.has('entry_only')};}
  if(state.filters.role.length<2){toast('Enter a role with at least two characters.',true);return;}
  state.busy='discover';state.error='';go('jobs');render();
  try {
    const result=await api('/api/jobs/discover',{method:'POST',body:JSON.stringify(state.filters)});
    state.jobs=result.jobs;state.sources=result.sources;state.fetched=result.fetched_at;state.fetchedCount=result.fetched_count;state.selected=state.jobs[0]?.id||null;
    if(result.sources.some(s=>!s.ok))toast('Some boards were unavailable. Available source results are shown.');
  }catch(e){state.error=e.message;toast(e.message,true);}finally{state.busy=null;render();}
}

async function analyseJob(id, previousId=null) {
  if(isBusy()||state.uploading)return;
  state.busy='analyse';state.error='';state.receipt=null;render();
  try {
    const params=new URLSearchParams({expected_version:state.candidate?.profile_version||''});
    if(previousId)params.set('reuse_assessment',previousId);
    else {const job=state.jobs.find(j=>j.id===id);if(job?.job_version)params.set('expected_job',job.job_version);}
    const record=await api(`/api/jobs/${encodeURIComponent(id)}/analyse?${params}`,{method:'POST'});
    state.record=record;state.records.set(record.id,record);state.tab='comparison';
    await refresh();state.busy=null;go(`assessment/${record.id}`);render();
    toast(record.enhancement_status==='unchanged'?'Assessment saved. No verified content improvements were accepted; source wording was retained.':'Your role assessment and tailored PDF are saved.');
  } catch(e){state.error=e.message;toast(e.message,true);}finally{state.busy=null;render();}
}

async function openRecord(id) {
  state.record=state.records.get(id)||null;state.tab='analysis';state.receipt=null;
  if(!state.record){try{state.record=await api(`/api/history/${encodeURIComponent(id)}`);state.records.set(id,state.record);}catch(e){toast(e.message,true);return;}}
  go(`assessment/${id}`);render();
}

document.addEventListener('click',async event=>{
  const button=event.target.closest('[data-action]');
  if(!button){if(event.target.closest('[data-drop]')){const zone=event.target.closest('[data-drop]');zone.dataset.drop==='modal'?$('#resume-file')?.click():openUpload();}return;}
  const action=button.dataset.action;
  if(action==='menu') {const open=$('#sidebar').classList.toggle('open');button.setAttribute('aria-expanded',String(open));updateSidebarAccess();return;}
  if(action==='dismiss-toast'){$('#toast-region').innerHTML='';return;}
  if(action==='upload'){openUpload();return;}
  if(action==='choose-file'){$('#resume-file').click();return;}
  if(action==='remove-file'){state.selectedFile=null;$('#selected-file').innerHTML='';$('#resume-file').value='';return;}
  if(action==='close-modal'){if(!state.uploading){modal.close();$('#modal-content').classList.remove('pdf-content');}return;}
  if(action==='review-profile'){go('resume');return;}
  if(action==='confirm-profile'){
    if(isBusy()||state.uploading)return;
    state.busy='confirm';button.disabled=true;
    try{await api('/api/profile',{method:'PUT',body:JSON.stringify({profile:state.candidate.profile,preferred_role:state.candidate.preferred_role,confirm:true,expected_version:state.candidate.profile_version})});await refresh();state.busy=null;await discoverJobs();}
    catch(e){toast(e.message,true);}finally{state.busy=null;render();}return;
  }
  if(action==='find-jobs'){await discoverJobs();return;}
  if(action==='select-job'){state.selected=button.dataset.id;render();if(window.matchMedia('(max-width:570px)').matches){$('.job-detail')?.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth',block:'start'});}return;}
  if(action==='analyse-job'){await analyseJob(button.dataset.id);return;}
  if(action==='prepare-updated'){await analyseJob(state.record.job.id,state.record.id);return;}
  if(action==='edit-profile'){if(isBusy()||state.uploading){toast('Wait for the current operation to finish.');return;}state.editing=true;go('resume');render();return;}
  if(action==='cancel-edit'){state.editing=false;render();return;}
  if(action==='preview-original'){previewPDF('/api/resume/original','Your original resume');return;}
  if(action==='preview-original-record'){previewPDF(`/api/history/${state.record.id}/pdf?original=true&inline=true`,'Original resume for this assessment');return;}
  if(action==='preview-pdf'){previewPDF(`/api/history/${state.record.id}/pdf?inline=true`,'Your tailored resume');return;}
  if(action==='open-record'){await openRecord(button.dataset.id);return;}
  if(action==='view-history'){go('history');return;}
  if(action==='back-jobs'){go('jobs');return;}
  if(action==='tab'){state.tab=button.dataset.tab;render();$(`#tab-${state.tab}`)?.focus({preventScroll:true});return;}
});

document.addEventListener('submit',async event=>{
  const form=event.target;
  if(!['upload-form','search-form','profile-form','review-form'].includes(form.id))return;
  event.preventDefault();
  if(form.id==='search-form'){await discoverJobs(form);return;}
  if(form.id==='upload-form'){
    if(state.uploading||isBusy())return;
    if(!state.selectedFile){$('#upload-error').innerHTML='<div class="field-error" role="alert">Choose a PDF resume first.</div>';return;}
    state.uploading=true;
    $$('button,input',form).forEach(el=>el.disabled=true);
    $('#upload-error').innerHTML='';
    $('#upload-progress').innerHTML=`<div class="upload-busy" role="status"><span class="spinner"></span><div>Reading your experience with Gemini…<small>The PDF is processed once, then saved for future roles.</small></div></div>`;
    const data=new FormData();data.append('file',state.selectedFile);data.append('preferred_role',$('#upload-role').value.trim());
    try{
      const result=await api('/api/resume',{method:'POST',body:data});
      await refresh();state.filters.role=result.preferred_role;state.editing=false;state.jobs=[];state.fetched=null;state.selected=null;state.record=null;
      state.uploading=false;modal.close();go('resume');toast('Your resume is saved. Review the extracted details and confirm your profile.');
    }catch(e){$('#upload-error').innerHTML=`<div class="field-error" role="alert">${esc(e.message)}</div>`;}
    finally{state.uploading=false;if(modal.open){$$('button,input',form).forEach(el=>el.disabled=false);$('#upload-progress').innerHTML='';}render();}
    return;
  }
  if(form.id==='profile-form'){
    if(isBusy())return;
    const data=new FormData(form),profile={...state.candidate.profile};
    ['name','email','phone','location'].forEach(key=>profile[key]=String(data.get(key)).trim());
    profile.links=String(data.get('links')).split('\n').map(s=>s.trim()).filter(Boolean);
    profile.skills=[...new Set(String(data.get('skills')).split(',').map(s=>s.trim()).filter(Boolean))];
    profile.facts=[];let index=1;
    for(const section of sections){for(const text of String(data.get(section)).split(/\n\s*\n/).map(s=>s.trim()).filter(Boolean)){profile.facts.push({id:`f${index++}`,section,text});}}
    const btn=$('button[type="submit"]',form);btn.disabled=true;state.busy='save';
    try{await api('/api/profile',{method:'PUT',body:JSON.stringify({profile,preferred_role:String(data.get('preferred_role')).trim(),expected_version:state.candidate.profile_version})});await refresh();state.editing=false;state.jobs=[];state.fetched=null;state.selected=null;toast('Profile saved. Review and confirm it before finding jobs.');}
    catch(e){$('#profile-error').innerHTML=`<div class="field-error" role="alert">${esc(e.message)}</div>`;btn.disabled=false;state.busy=null;return;}
    finally{state.busy=null;}
    render();return;
  }
  if(form.id==='review-form'){
    if(isBusy())return;
    const data=Object.fromEntries(new FormData(form));delete data.understood;
    const btn=$('button[type="submit"]',form);btn.disabled=true;state.busy='submit';
    try{const receipt=await api(`/api/test-receiver/${state.record.id}`,{method:'POST',body:JSON.stringify(data)});state.receipt=receipt;await refresh();state.record=state.records.get(state.record.id);toast('Local test complete. No employer received an application.');}
    catch(e){$('#review-error').innerHTML=`<div class="field-error" role="alert">${esc(e.message)}</div>`;btn.disabled=false;state.busy=null;return;}
    finally{state.busy=null;}
    render();main.scrollIntoView({behavior:'auto',block:'start'});
  }
});

document.addEventListener('change',e=>{if(e.target.id==='resume-file')selectFile(e.target.files[0]);});
document.addEventListener('dragover',e=>{const zone=e.target.closest('[data-drop]');if(zone){e.preventDefault();if(!state.uploading)zone.classList.add('dragover');}});
document.addEventListener('dragleave',e=>{const zone=e.target.closest('[data-drop]');if(zone&&!zone.contains(e.relatedTarget))zone.classList.remove('dragover');});
document.addEventListener('drop',e=>{const zone=e.target.closest('[data-drop]');if(!zone)return;e.preventDefault();zone.classList.remove('dragover');if(state.uploading||isBusy())return;const file=e.dataTransfer.files[0];if(zone.dataset.drop==='modal')selectFile(file);else openUpload(file);});
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'&&$('#sidebar').classList.contains('open')){$('#sidebar').classList.remove('open');$('.mobile-menu').setAttribute('aria-expanded','false');updateSidebarAccess();$('.mobile-menu').focus();}

  const zone=e.target.closest('[data-drop]');if(zone&&e.target===zone&&['Enter',' '].includes(e.key)){e.preventDefault();zone.dataset.drop==='modal'?$('#resume-file').click():openUpload();}
  const tab=e.target.closest('[role="tab"]');if(tab&&['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const tabs=$$('[role="tab"]'),i=tabs.indexOf(tab);let next=e.key==='Home'?0:e.key==='End'?tabs.length-1:(i+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;state.tab=tabs[next].dataset.tab;render();$(`#tab-${state.tab}`).focus();}
});
$('.skip-link').addEventListener('click',e=>{e.preventDefault();main.focus();});
document.addEventListener('click',e=>{if($('#sidebar').classList.contains('open')&&!e.target.closest('.sidebar')&&!e.target.closest('.mobile-menu')){$('#sidebar').classList.remove('open');$('.mobile-menu').setAttribute('aria-expanded','false');updateSidebarAccess();}});
modal.addEventListener('cancel',e=>{if(state.uploading)e.preventDefault();});
modal.addEventListener('close',()=>{previewModule?.closePreview();$('#modal-content').classList.remove('pdf-content');});
window.addEventListener('hashchange',async()=>{
  $('#sidebar').classList.remove('open');$('.mobile-menu').setAttribute('aria-expanded','false');updateSidebarAccess();
  if(currentRoute()==='assessment'){const id=location.hash.split('/')[1];if(id&&state.record?.id!==id){await openRecord(id);return;}}
  render();window.scrollTo(0,0);
});

(async()=>{try{await refresh();if(currentRoute()==='assessment'){const id=location.hash.split('/')[1];state.record=state.records.get(id)||null;}render();}catch(e){main.innerHTML=empty('info','Your workspace is taking a moment.',e.message);$('#connection').textContent='Server unavailable';}})();
