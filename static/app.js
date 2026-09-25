'use strict';
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clone = x => JSON.parse(JSON.stringify(x));
const days = ['Dushanba','Seshanba','Chorshanba','Payshanba','Juma','Shanba'];
let state, page='dashboard', resource='teachers', view='all', viewId='', report=null, saving=false;
const entity = (kind,id) => state.project[kind].find(x=>x.id===id);
const name = (kind,id) => entity(kind,id)?.name || id;
const id = prefix => prefix+'_'+crypto.randomUUID().slice(0,8);
function toast(message){$('#toast').textContent=message;$('#toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').hidden=true,4500);}
async function api(path,method='GET',body){
  const r=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
  const data=await r.json();
  if(!r.ok){const d=data.detail;throw Error(typeof d==='string'?d:Array.isArray(d)?d.map(x=>typeof x==='string'?x:(x.loc?.join('.')+': '+x.msg)).join('\n'):JSON.stringify(data));}
  return data;
}
async function reload(){state=await api('/state');$('#school-name').textContent=state.project.school.name;$('#revision').textContent='Saved · revision '+state.revision;}
function heading(title,subtitle,buttons=''){return `<div class="page-heading"><div><span class="eyebrow">${esc(state.project.school.year)} / SCHOOL PLANNING</span><h1>${title}</h1><p class="subtitle">${subtitle}</p></div><div class="actions">${buttons}</div></div>`;}
function button(text,action,extra=''){return `<button class="button ${extra}" data-action="${action}">${text}</button>`;}
function stat(title,value,note,icon){return `<div class="stat"><div class="stat-top">${title}<span class="stat-icon">${icon}</span></div><div class="stat-value">${value}</div><div class="stat-note">${note}</div></div>`;}
function isStale(){return !!state.draft && state.activity.some(x=>x.text.startsWith('School inputs saved') && x.at>state.draft.generated_at);}
function field(label,key,value='',type='text',help='',extra=''){return `<label class="field">${label}<input name="${key}" type="${type}" value="${esc(value)}" ${extra}><small>${help}</small></label>`;}
function area(label,key,value,help=''){return `<label class="field full">${label}<textarea name="${key}">${esc(value)}</textarea><small>${help}</small></label>`;}
function select(label,key,items,value,allowAll=false,multiple=false){
  return `<label class="field">${label}<select name="${key}" ${multiple?'multiple':''}>${allowAll?'<option value="">All / any</option>':''}${items.map(x=>`<option value="${esc(x.id)}" ${(multiple?(value||[]).includes(x.id):x.id===value)?'selected':''}>${esc(x.name)}</option>`).join('')}</select>${multiple?'<small>Ctrl / Cmd + click to select multiple options.</small>':''}</label>`;
}
function checks(label,key,items,values){return `<div class="field full">${label}<div class="checkboxes">${items.map((x,i)=>`<label><input type="checkbox" name="${key}" value="${i}" ${values.includes(i)?'checked':''}>${esc(x)}</label>`).join('')}</div></div>`;}
function dialog(title,html,submit,text='Save changes'){
  $('#editor-title').textContent=title;$('#editor-body').innerHTML=html;$('#form-error').hidden=true;$('#submit-dialog').textContent=text;$('#submit-dialog').disabled=false;
  $('#editor-form').onsubmit=async e=>{e.preventDefault();if(saving)return;saving=true;$('#submit-dialog').disabled=true;try{if(await submit(new FormData(e.target))===false)return;$('#editor').close();await render();}catch(err){$('#form-error').textContent=err.message;$('#form-error').hidden=false;}finally{saving=false;$('#submit-dialog').disabled=false;}};
  $('#editor').showModal();
}
async function saveProject(project){const hadDraft=!!state.draft;state=await api('/project','PUT',{revision:state.revision,project});report=null;await reload();if(hadDraft){toast('Inputs saved. Adapting the whole-school timetable…');await generate();}else toast('Inputs saved.');}
function availabilityText(items=[]){return items.map(x=>`${x.day+1} ${x.start} ${x.end}`).join('\n');}
function availability(value){return String(value||'').trim().split('\n').filter(x=>x.trim()).map(line=>{const v=line.trim().split(/\s+/);if(v.length!==3)throw Error('Availability format: day number, start, end. Example: 1 08:00 10:00');return {day:Number(v[0])-1,start:v[1],end:v[2]};});}
function reqFor(occurrence){return entity('requirements',occurrence.slice(0,occurrence.lastIndexOf(':')));}
function scopeLabel(r){return [r.class_id&&name('classes',r.class_id),r.subject_id&&name('subjects',r.subject_id),r.teacher_id&&name('teachers',r.teacher_id),r.group_id].filter(Boolean).join(' · ')||'Whole school';}
function ruleSummary(r){return `${scopeLabel(r)} · ${r.kind==='max_daily'?`maximum ${r.limit} periods / day`:r.kind} ${r.days.length?r.days.map(d=>days[d]).join(', '):'any day'}${r.periods.length?' · periods '+r.periods.join(', '):''}`;}
function ruleRow(r,compact=false){return `<div class="rule-row"><div class="checkmark">${r.enabled?'✓':'–'}</div><div class="text"><h3>${esc(r.name)}</h3><p>${esc(ruleSummary(r))}</p></div><span class="badge ${r.strength==='preferred'?'blue':''}">${r.enabled?(r.strength==='required'?'Required':`Preferred · ${r.weight}`):'Disabled'}</span>${compact?'':`<div class="actions"><button class="button small" data-rule-edit="${r.id}">Edit</button><button class="button small" data-rule-toggle="${r.id}">${r.enabled?'Disable':'Enable'}</button><button class="button small danger" data-delete="rules:${r.id}">Delete</button></div>`}</div>`;}
async function render(){
  document.querySelectorAll('[data-page]').forEach(b=>b.classList.toggle('active',b.dataset.page===page&&(!b.dataset.resource||b.dataset.resource===resource)));
  if(page==='timetable')renderTimetable();
  else if(page==='dashboard')renderDashboard();
  else if(page==='assignments')renderAssignments();
  else if(page==='requirements')renderRequirements();
  else if(page==='workload')await renderWorkload();
  else if(page==='rules')renderRules();
  else if(page==='people')renderResources();
  else if(page==='versions')await renderVersions();
  else if(page==='research'||page==='stages')await renderDocument();
}
function renderTimetable(){
  const p=state.project,d=state.draft,stale=isStale();
  if(view!=='all'&&!p[view].some(x=>x.id===viewId))viewId=p[view][0]?.id||'';
  const reportNow=report || d?.report;
  const total=p.requirements.reduce((s,r)=>s+r.weekly,0),split=p.requirements.filter(r=>r.parts.length===2).reduce((s,r)=>s+r.weekly,0);
  $('#main').innerHTML=heading('A place for every lesson.','Build a balanced week, with every teacher and group in the right place.',button('↗ Export','export')+button('✦ Generate timetable','generate','primary'))+
  `<div class="stats">${stat('Weekly sessions',total,'Across '+p.classes.length+' classes','▤')}${stat('Teachers',p.teachers.length,'Assigned across your school','♧')}${stat('Split sessions',split,'Two groups, one shared period','◫')}${stat('Active rules',p.rules.filter(r=>r.enabled).length,'Your school’s scheduling priorities','⌘')}</div>`+
  `<div class="notice"><span>ⓘ</span><div><strong>${stale?'Inputs changed — this draft is stale.':'School policy review'}</strong> ${stale?'Generate again before moving or publishing lessons.':esc(p.school.curriculum_reference)} <a href="#research" data-action="research">View research</a></div></div>`+
  `<section class="panel"><div class="panel-head"><div><h3>Weekly timetable <span class="badge ${stale?'warn':''}">${stale?'Stale draft':d?d.status==='OPTIMAL'?'Optimal for configured priorities':'Validated draft':'Ready to generate'}</span></h3><span class="muted" style="font-size:10px">${d?'Select a session to move it or lock both groups together.':'Your generated lessons will appear here.'}</span></div><div class="filters"><select id="view-kind" aria-label="Timetable view"><option value="all" ${view==='all'?'selected':''}>All classes · whole week</option><option value="classes" ${view==='classes'?'selected':''}>By class</option><option value="teachers" ${view==='teachers'?'selected':''}>By teacher</option><option value="rooms" ${view==='rooms'?'selected':''}>By room</option></select><select id="view-id" aria-label="Timetable resource" ${view==='all'?'hidden':''}>${(p[view]||[]).map(x=>`<option value="${x.id}" ${x.id===viewId?'selected':''}>${esc(x.name)}</option>`).join('')}</select>${button('Print','print','small')}${button('Save version','version','small')}${button('Publish','publish','small')}</div></div><div id="grid"></div><div class="legend">${p.subjects.slice(0,7).map(s=>`<span style="--c:${s.color}">${esc(s.name)}</span>`).join('')}</div></section>`+
  `<div class="bottom-grid"><section class="panel"><div class="panel-head"><h3>Timetable health</h3><span class="badge ${reportNow?.errors?.length?'warn':''}">${reportNow?.errors?.length?reportNow.errors.length+' issues':d?'Checked independently':'Awaiting generation'}</span></div><div class="panel-body">${reportNow?.errors?.length?`<div class="error">${esc(reportNow.errors.join('\n'))}</div>`:''}${d&&!stale?`<div class="check-row"><span class="checkmark">✓</span><div>All ${d.placements.length} sessions assigned<small>Whole-class and parallel groups included</small></div></div><div class="check-row"><span class="checkmark">✓</span><div>No teacher, room or class overlaps<small>Checked using actual lesson times</small></div></div><div class="check-row"><span class="checkmark">${d.report.score? '◌':'✓'}</span><div>${d.report.score} preference penalty points<small>Lower is better; required rules are never traded off</small></div></div>`:`<p class="help">Generate a timetable to check conflicts and see preference trade-offs.</p>`}${reportNow?.penalties?.length?`<ul class="report-list">${reportNow.penalties.map(x=>`<li>${esc(x.name)}: ${x.points} points</li>`).join('')}</ul>`:''}<details><summary class="help">Policy notes and input warnings (${reportNow?.warnings?.length||0})</summary><ul class="report-list">${(reportNow?.warnings||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ul></details></div></section><section class="panel"><div class="panel-head"><h3>Rules shaping this week</h3>${button('Manage rules →','rules','small quiet')}</div><div class="panel-body">${p.rules.slice(0,3).map(r=>ruleRow(r,true)).join('')||'<p class="help">Add your first school rule.</p>'}</div></section></div>`;
  renderGrid();
  if(d?.changes?.length){const section=document.createElement('section');section.className='panel panel-body';section.innerHTML='<h3>Changes from your last manual choice</h3>'+d.changes.map(x=>`<p>${esc(reqFor(x.occurrence)?.name||x.occurrence)}: ${esc(days[x.before.day])} ${x.before.period} → ${esc(days[x.after.day])} ${x.after.period}${JSON.stringify(x.before.rooms)!==JSON.stringify(x.after.rooms)?' · room changed':''}</p>`).join('');$('#main').append(section);}
  $('#view-kind').onchange=e=>{view=e.target.value;viewId='';renderTimetable();};$('#view-id').onchange=e=>{viewId=e.target.value;renderGrid();};
}
function renderGrid(){
  if(view==='all'){renderSchoolGrid();return;}
  const p=state.project,d=state.draft;
  const c=view==='classes'?entity('classes',viewId):null;
  const shift=c?p.school.shifts.find(s=>s.id===c.shift_id):null;
  const slots=shift?shift.periods.map((s,i)=>({period:i+1,start:s.start,end:s.end,shift:shift.id})):p.school.shifts.flatMap(sh=>sh.periods.map((s,i)=>({period:i+1,start:s.start,end:s.end,shift:sh.id}))).sort((a,b)=>a.start.localeCompare(b.start));
  const placements=(d?.placements||[]).filter(x=>{const r=reqFor(x.occurrence);return r&&(view==='classes'?r.class_id===viewId:view==='teachers'?r.parts.some(a=>a.teacher_id===viewId):x.rooms.includes(viewId));});
  const cell=(slot,day)=>{
    const items=placements.filter(x=>{const r=reqFor(x.occurrence),cl=entity('classes',r.class_id);return cl.shift_id===slot.shift&&x.day===day&&x.period===slot.period;});
    const continuing=placements.some(x=>{const r=reqFor(x.occurrence);return entity('classes',r.class_id).shift_id===slot.shift&&x.day===day&&x.period<slot.period&&x.period+r.duration>slot.period;});
    return `<td data-drop-day="${day}" data-drop-period="${slot.period}" data-drop-shift="${slot.shift}">${items.map(x=>{
      const r=reqFor(x.occurrence),s=entity('subjects',r.subject_id),cl=entity('classes',r.class_id);
      return `<button class="lesson" draggable="${!x.locked&&!isStale()}" data-session="${esc(x.occurrence)}" style="--lesson-color:${s.color}" aria-label="${esc(cl.name+' '+s.name+' '+days[day]+' period '+x.period)}"><strong>${esc(s.name)}</strong>${x.locked?'<span class="lock">◆</span>':''}${r.parts.length===2?'<span class="split-label">⇄ 2 groups · simultaneous</span>':''}${r.duration===2?'<span class="split-label"> · 2 periods</span>':''}${view!=='classes'?`<small>${esc(cl.name)}</small>`:''}${r.parts.map((a,i)=>`<div class="part"><b>${r.parts.length===2?esc(cl.partitions.find(pt=>pt.id===r.partition_id)?.groups.find(g=>g.id===a.group_id)?.name||a.group_id)+' · ':''}${esc(name('teachers',a.teacher_id))}</b><br>${esc(name('rooms',x.rooms[i]))}</div>`).join('')}</button>`;
    }).join('')||`<div class="free-slot">${continuing?'↳':c&&!c.days.includes(day)?'—':'·'}</div>`}</td>`;
  };
  $('#grid').innerHTML=`<div class="table-scroll"><table class="timetable"><thead><tr><th>PERIOD</th>${days.map(d=>`<th><strong>${d}</strong></th>`).join('')}</tr></thead><tbody>${slots.map(slot=>`<tr><td>${slot.period}<small>${slot.start}<br>${slot.end}</small>${!c?`<small>${esc(p.school.shifts.find(s=>s.id===slot.shift).name)}</small>`:''}</td>${days.map((_,d)=>cell(slot,d)).join('')}</tr>`).join('')}</tbody></table></div>`;
  $('#grid').ondragstart=e=>{const b=e.target.closest('[data-session]');if(b)e.dataTransfer.setData('text/plain',b.dataset.session);};
  $('#grid').ondragover=e=>{const cell=e.target.closest('[data-drop-day]');if(cell){e.preventDefault();cell.classList.add('drop-target');}};
  $('#grid').ondragleave=e=>e.target.closest('[data-drop-day]')?.classList.remove('drop-target');
  $('#grid').ondrop=e=>{e.preventDefault();document.querySelectorAll('.drop-target').forEach(x=>x.classList.remove('drop-target'));const cell=e.target.closest('[data-drop-day]'),eid=e.dataTransfer.getData('text/plain');if(cell&&eid){const r=reqFor(eid);if(!r)return;if(entity('classes',r.class_id).shift_id!==cell.dataset.dropShift){toast('Move within the class’s assigned shift.');return;}editSession(eid,+cell.dataset.dropDay,+cell.dataset.dropPeriod);}};
}
async function generate(){
  const b=document.querySelector('[data-action="generate"]');if(b){b.disabled=true;b.innerHTML='<span class="spinner"></span> Scheduling…';}
  try{const result=await api('/generate','POST',{revision:state.revision,seconds:120,preserve:true});if(result.ok){state=result.state;report=null;await reload();toast('Timetable generated. All hard constraints passed.');}else{report=result.result.report;page='timetable';toast(result.result.status==='UNKNOWN'?'Search ended without a complete result.':'Review the timetable health report.');}await render();}catch(e){toast(e.message);await reload();await render();}
}
function renderRequirementsLegacy(){
  const rows=state.project.requirements.map(r=>`<tr><td><strong>${esc(name('classes',r.class_id))}</strong></td><td>${esc(name('subjects',r.subject_id))}<small>${esc(r.name)}</small></td><td>${r.weekly} × ${r.duration}<small>${r.weekly*r.duration} student periods</small></td><td><span class="badge ${r.parts.length===2?'blue':''}">${r.parts.length===2?'2 synchronized groups':'Whole class'}</span></td><td>${r.parts.map(a=>esc(name('teachers',a.teacher_id))).join('<br>')}</td><td><div class="actions"><button class="button small" data-req="${r.id}">Edit</button><button class="button small danger" data-delete="requirements:${r.id}">Delete</button></div></td></tr>`).join('');
  $('#main').innerHTML=heading('Teaching plan','Define the hours, teachers and groups before placing lessons.',button('+ Add requirement','add-req','primary'))+`<div class="notice">ⓘ ${esc(state.project.school.curriculum_reference)}. One split period counts once for the class and once for each teacher.</div><section class="panel table-scroll"><table class="data-table"><thead><tr><th>Class</th><th>Subject</th><th>Sessions / week</th><th>Delivery</th><th>Assigned teachers</th><th></th></tr></thead><tbody>${rows}</tbody></table>${!rows?'<div class="empty">Add the first class teaching requirement.</div>':''}</section>`;
}
async function renderWorkload(){
  const data=await api('/workload');
  const table=(title,rows,teachers)=>`<section class="panel table-scroll"><div class="panel-head"><h3>${title}</h3></div><table class="data-table"><thead><tr><th>Name</th><th>Approved periods</th><th>Plan periods</th><th>Scheduled</th><th>Remaining</th><th></th></tr></thead><tbody>${rows.map(r=>`<tr><td>${esc(r.name)}</td><td>${r.approved??'Not specified'}</td><td>${r.required}${r.allocation_difference?` <span class="badge warn">Mismatch ${r.allocation_difference>0?'+':''}${r.allocation_difference}</span>`:''}</td><td>${data.current?r.scheduled:'Awaiting current schedule'}</td><td>${r.remaining}</td><td>${teachers?`<button class="button small" data-allocation="${r.id}">Set approved hours</button>`:''}</td></tr>`).join('')}</tbody></table></section>`;
  $('#main').innerHTML=heading('Every class. Every teaching hour.','One period counts once for a class and once for each teacher teaching a split group.',button('Paste teaching CSV','teaching-csv')+button('Generate / repair','generate','primary'))+table('Classes',data.classes,false)+table('Teachers',data.teachers,true);
}
function importTeaching(){
  dialog('Import the school teaching plan',area('CSV rows','csv_text','id,class_id,subject_id,weekly,teacher_id,room_ids,duration,max_daily','Use existing resource IDs. Separate eligible room IDs with |. Optional approved_weekly column sets each teacher’s total allocation. Optional split columns: partition_id, group_id, teacher_2_id, group_2_id, room_2_ids. Export a project from School resources to find IDs.')+'<div id="import-preview"></div>',async f=>{
    if(!importTeaching.preview || importTeaching.text!==f.get('csv_text')){
      const result=await api('/import/teaching-preview','POST',{revision:state.revision,csv_text:f.get('csv_text')});
      importTeaching.preview=result;importTeaching.text=f.get('csv_text');
      $('#import-preview').textContent=`${result.project.requirements.length} requirements for ${result.workload.classes.length} classes. ${result.report.errors.join(' ')} ${result.report.warnings.join(' ')}`;
      $('#submit-dialog').textContent='Apply reviewed teaching plan'; return false;
    }
    await saveProject(importTeaching.preview.project);
  },'Preview / apply teaching plan');
  importTeaching.preview=null;
}
function editRequirement(rid,classId){
  const p=clone(state.project),existing=p.requirements.find(r=>r.id===rid);
  if(!p.classes.length||!p.subjects.length||!p.teachers.length||!p.rooms.length){toast('Add classes, subjects, teachers and rooms first.');return;}
  const r=existing||{id:id('lesson'),name:'',class_id:classId||planClass||p.classes[0].id,subject_id:p.subjects[0].id,weekly:2,duration:1,max_daily:1,partition_id:null,parts:[]};
  const main=`<div class="form-grid">${field('Requirement name','name',r.name,'text','Optional descriptive label')}${select('Class','class_id',p.classes,r.class_id)}${select('Subject','subject_id',p.subjects,r.subject_id)}${select('Delivery','delivery',[{id:'whole',name:'Whole class'},{id:'split',name:'Two simultaneous groups'}],r.partition_id?'split':'whole')}${field('Sessions per week','weekly',r.weekly,'number','Each double session counts as two periods.','min="1" max="40" required')}${select('Session duration','duration',[{id:'1',name:'One period'},{id:'2',name:'Two consecutive periods'}],String(r.duration))}${field('Maximum subject periods per day','max_daily',r.max_daily,'number','','min="1" max="10" required')}</div><div id="parts-editor"></div>`;
  dialog(existing?'Edit teaching requirement':'Add teaching requirement',main,async f=>{
    const cid=f.get('class_id'),sid=f.get('subject_id'),cl=p.classes.find(c=>c.id===cid),split=f.get('delivery')==='split';
    const partitionId=split?(r.partition_id&&r.class_id===cid?r.partition_id:r.id+'_groups'):null;
    const parts=[];
    if(split){
      const partition={id:partitionId,name:p.subjects.find(s=>s.id===sid).name+' groups',groups:[0,1].map(n=>({id:partitionId+'_'+(n+1),name:f.get('group_name_'+n),size:Number(f.get('size_'+n))}))};
      const oldPartition=cl.partitions.find(x=>x.id===partitionId);
      if(oldPartition){partition.groups.forEach((g,n)=>g.id=oldPartition.groups[n].id);cl.partitions[cl.partitions.indexOf(oldPartition)]=partition;}else cl.partitions.push(partition);
      for(let n=0;n<2;n++)parts.push({group_id:partition.groups[n].id,teacher_id:f.get('teacher_'+n),room_ids:f.getAll('rooms_'+n)});
    }else parts.push({group_id:'*',teacher_id:f.get('teacher_0'),room_ids:f.getAll('rooms_0')});
    const data={...r,name:f.get('name').trim()||cl.name+' · '+p.subjects.find(s=>s.id===sid).name,class_id:cid,subject_id:sid,weekly:Number(f.get('weekly')),duration:Number(f.get('duration')),max_daily:Number(f.get('max_daily')),partition_id:partitionId,parts};
    if(existing)p.requirements[p.requirements.indexOf(existing)]=data;else p.requirements.push(data);
    await saveProject(p);
  });
  const update=()=>{
    const form=$('#editor-form'),cid=form.elements.class_id.value,sid=form.elements.subject_id.value,split=form.elements.delivery.value==='split',cl=p.classes.find(c=>c.id===cid),partition=cl.partitions.find(pt=>pt.id===r.partition_id);
    const teachers=p.teachers.filter(t=>t.subjects.includes(sid)).map(t=>({...t,name:t.name+' · '+p.requirements.reduce((n,r)=>n+r.parts.filter(a=>a.teacher_id===t.id).length*r.weekly*r.duration,0)+' / '+(t.assigned_weekly??t.max_weekly)+' periods'}));
    $('#parts-editor').innerHTML=(teachers.length?'':'<p class="error">No teacher is qualified for this subject. Add the qualification under School resources.</p>')+[...Array(split?2:1)].map((_,n)=>`<div class="subform"><h3>${split?'Group '+(n+1):'Whole-class assignment'}</h3><div class="form-grid">${split?field('Group name','group_name_'+n,partition?.groups[n]?.name||`${n+1}-guruh`,'text','','required')+field('Students in this group','size_'+n,partition?.groups[n]?.size||(n===0?Math.ceil(cl.size/2):Math.floor(cl.size/2)),'number','Both groups must total '+cl.size,'min="1" required'):''}${select('Assigned teacher','teacher_'+n,teachers,r.parts[n]?.teacher_id||teachers[0]?.id)}${select('Eligible rooms','rooms_'+n,p.rooms.map(x=>({id:x.id,name:x.name+' · '+x.capacity+' seats'})),r.parts[n]?.room_ids||[p.rooms[0].id],false,true)}</div></div>`).join('');
  };
  ['class_id','subject_id','delivery'].forEach(k=>$('#editor-form').elements[k].onchange=update);update();
}
function renderRules(){
  $('#main').innerHTML=heading('Your school. Your rules.','Set firm restrictions and preferences that the scheduler can explain.',button('+ Add rule','add-rule','primary'))+`<div class="notice">Required rules can make a timetable impossible. Preferred rules contribute penalty points. Both are checked when you move a lesson.</div><section class="panel"><div class="panel-body">${state.project.rules.map(r=>ruleRow(r)).join('')||'<div class="empty">For example: never put Informatics on Monday.</div>'}</div></section>`;
}
function editRule(rid){
  const p=clone(state.project),existing=p.rules.find(r=>r.id===rid),r=existing||{id:id('rule'),name:'',enabled:true,kind:'forbid',strength:'required',class_id:null,subject_id:null,teacher_id:null,group_id:null,days:[0],periods:[],limit:1,weight:10,note:''};
  const groups=p.classes.flatMap(c=>c.partitions.flatMap(pt=>pt.groups.map(g=>({id:g.id,name:`${c.name} · ${pt.name} · ${g.name}`}))));
  dialog(existing?'Edit scheduling rule':'Add scheduling rule',`<div class="form-grid">${field('Rule name','name',r.name,'text','','required')}${select('Rule type','kind',[{id:'forbid',name:'Never schedule at these times'},{id:'prefer',name:'Prefer these times'},{id:'avoid',name:'Avoid these times'},{id:'max_daily',name:'Maximum matching periods per day'}],r.kind)}${select('Class','class_id',p.classes,r.class_id,true)}${select('Subject','subject_id',p.subjects,r.subject_id,true)}${select('Teacher','teacher_id',p.teachers,r.teacher_id,true)}${select('Group','group_id',groups,r.group_id,true)}${select('Strength','strength',[{id:'required',name:'Required'},{id:'preferred',name:'Preferred'}],r.strength)}${field('Preference weight','weight',r.weight,'number','Penalty per affected session, or per excess period.','min="1" max="1000"')}${field('Maximum periods / day (limit rule only)','limit',r.limit,'number','Teacher scope counts across their classes; otherwise per class.','min="0" max="60"')}${checks('Days (none means any day)','days',days,r.days)}${checks('Periods (none means any period)','periods',Array.from({length:10},(_,i)=>String(i+1)),r.periods.map(x=>x-1))}${area('Reason / policy source','note',r.note,'All chosen scopes are combined. A group rule affects the complete synchronized session.')}</div>`,async f=>{
    const data={...r,name:f.get('name'),kind:f.get('kind'),strength:f.get('strength'),class_id:f.get('class_id')||null,subject_id:f.get('subject_id')||null,teacher_id:f.get('teacher_id')||null,group_id:f.get('group_id')||null,days:f.getAll('days').map(Number),periods:f.getAll('periods').map(x=>Number(x)+1),limit:Number(f.get('limit')),weight:Number(f.get('weight')),note:f.get('note')};
    if(existing)p.rules[p.rules.indexOf(existing)]=data;else p.rules.push(data);await saveProject(p);
  });
  $('#editor-form').elements.kind.onchange=e=>{const f=$('#editor-form');f.elements.strength.value=e.target.value==='forbid'?'required':'preferred';if(e.target.value==='max_daily')f.querySelectorAll('[name="periods"]').forEach(x=>x.checked=false);};
}
function renderResources(){
  const p=state.project,items=p[resource];
  const detail=x=>resource==='teachers'?`${x.subjects.map(s=>name('subjects',s)).join(', ')} · ${x.max_daily}/day · ${x.max_weekly}/week · ${x.unavailable.length} unavailable blocks`:resource==='classes'?`Grade ${x.grade} · ${x.size} students · ${x.language} · ${x.partitions.length} partitions`:resource==='rooms'?`${x.capacity} seats · ${x.kind} · ${x.unavailable.length} unavailable blocks`:x.category;
  $('#main').innerHTML=heading('The people and places.','Maintain your classes, qualified teachers, subjects and available rooms.',button('+ Add '+resource.replace(/s$/,''),'add-resource','primary'))+`<div class="tabs">${['teachers','classes','subjects','rooms'].map(k=>`<button data-resource="${k}" class="${resource===k?'active':''}">${k[0].toUpperCase()+k.slice(1)} (${p[k].length})</button>`).join('')}</div><section class="panel table-scroll"><table class="data-table"><thead><tr><th>Name</th><th>Details</th><th></th></tr></thead><tbody>${items.map(x=>`<tr><td><strong>${esc(x.name)}</strong><small>${esc(x.id)}</small></td><td>${esc(detail(x))}</td><td><div class="actions"><button class="button small" data-entity="${x.id}">Edit</button><button class="button small danger" data-delete="${resource}:${x.id}">Delete</button></div></td></tr>`).join('')}</tbody></table></section><div class="actions">${button('Import project JSON','import')}${button('Export project JSON','export-project')}</div>`;
}
function editEntity(eid){
  const p=clone(state.project),existing=p[resource].find(x=>x.id===eid),defaults={teachers:{subjects:[],max_daily:6,max_weekly:30,unavailable:[]},classes:{grade:10,language:'uz',size:30,shift_id:p.school.shifts[0].id,days:[0,1,2,3,4,5],max_daily:6,max_weekly:36,partitions:[]},subjects:{color:'#537bdf',category:'general'},rooms:{capacity:30,kind:'general',unavailable:[]}},x=existing||{id:id(resource),name:'',...defaults[resource]};
  let html=field('Name','name',x.name,'text','','required');
  if(resource==='teachers')html+=select('Qualified subjects','subjects',p.subjects,x.subjects,false,true)+field('Daily teaching period limit','max_daily',x.max_daily,'number','','min="1" max="20" required')+field('Weekly teaching period limit','max_weekly',x.max_weekly,'number','Use the school-approved teaching allocation, not total working hours.','min="1" max="120" required')+area('Unavailable times','unavailable',availabilityText(x.unavailable),'One line per block: day 1–6, start, end. Example: 1 08:00 10:00');
  if(resource==='classes')html+=field('Grade','grade',x.grade,'number','','min="1" max="11" required')+field('Students','size',x.size,'number','Existing group sizes must still sum to this total.','min="1" max="100" required')+select('Teaching language','language',[{id:'uz',name:'Uzbek'},{id:'ru',name:'Russian'},{id:'kk',name:'Karakalpak'},{id:'other',name:'Other'}],x.language)+select('Teaching shift','shift_id',p.school.shifts,x.shift_id)+field('Daily class period limit','max_daily',x.max_daily,'number','School policy setting; review against current applicable requirements.','min="1" max="10" required')+field('Weekly class period limit','max_weekly',x.max_weekly,'number','','min="1" max="60" required')+checks('Teaching days','days',days,x.days)+area('Subject partitions (advanced JSON)','partitions',JSON.stringify(x.partitions,null,2),'Normally created in Teaching plan when you choose two groups. Edit here to adjust existing group sizes.');
  if(resource==='rooms')html+=field('Seats','capacity',x.capacity,'number','','min="1" max="500" required')+field('Room type','kind',x.kind)+area('Unavailable times','unavailable',availabilityText(x.unavailable),'One line per block: day 1–6, start, end. Example: 3 09:00 12:00');
  if(resource==='subjects')html+=field('Timetable color','color',x.color,'color')+select('Split-eligibility category','category',['general','foreign','informatics','pe','technology','russian','uzbek','military','vocational'].map(v=>({id:v,name:v})),x.category);
  dialog(existing?'Edit '+resource.replace(/s$/,''):'Add '+resource.replace(/s$/,''),`<div class="form-grid">${html}</div>`,async f=>{
    const data={...x,name:f.get('name')};
    if(resource==='teachers')Object.assign(data,{subjects:f.getAll('subjects'),max_daily:+f.get('max_daily'),max_weekly:+f.get('max_weekly'),unavailable:availability(f.get('unavailable'))});
    if(resource==='classes')Object.assign(data,{grade:+f.get('grade'),size:+f.get('size'),language:f.get('language'),shift_id:f.get('shift_id'),max_daily:+f.get('max_daily'),max_weekly:+f.get('max_weekly'),days:f.getAll('days').map(Number),partitions:JSON.parse(f.get('partitions'))});
    if(resource==='rooms')Object.assign(data,{capacity:+f.get('capacity'),kind:f.get('kind'),unavailable:availability(f.get('unavailable'))});
    if(resource==='subjects')Object.assign(data,{color:f.get('color'),category:f.get('category')});
    if(existing)p[resource][p[resource].indexOf(existing)]=data;else p[resource].push(data);await saveProject(p);
  });
}
function editSettings(){
  const p=clone(state.project),s=p.school;
  dialog('School settings',`${field('School name','name',s.name,'text','','required')}${field('Academic year','year',s.year)}${field('Approved curriculum reference','curriculum_reference',s.curriculum_reference)}${area('Policy review note','policy_note',s.policy_note)}${area('Shifts and bell times','shifts',JSON.stringify(s.shifts,null,2),'Each shift has id, name and ordered periods with start/end (HH:MM). Maximum two shifts. Teachers and rooms are checked across real clock times.')}<p class="help">Ordinary demo bells use 45-minute lessons, 10-minute short breaks and a 20-minute long break. Confirm the approved settings for your school.</p>`,async f=>{p.school={name:f.get('name'),year:f.get('year'),curriculum_reference:f.get('curriculum_reference'),policy_note:f.get('policy_note'),shifts:JSON.parse(f.get('shifts'))};await saveProject(p);});
}
function editSession(eid,day,period){
  const x=state.draft?.placements.find(p=>p.occurrence===eid),r=reqFor(eid);if(!x||!r)return;
  const c=entity('classes',r.class_id),shift=state.project.school.shifts.find(s=>s.id===c.shift_id);
  dialog(name('subjects',r.subject_id)+' · '+c.name,`<p class="help">${r.parts.length===2?'Both groups move together. Your choice is locked; other unlocked lessons adapt around it.':'Choose a time and room. Other unlocked lessons will be rearranged around your choice.'}</p><div class="actions" style="margin-bottom:20px"><button type="button" class="button" id="lock-session">${x.locked?'Unlock session':'Lock session'}</button><span class="badge">${x.locked?'Locked':'Unlocked'}</span></div>${isStale()?'<div class="notice">This draft is stale. You can unlock a lesson, then generate again.</div>':''}<div class="form-grid">${select('Day','day',days.map((d,i)=>({id:String(i),name:d})),String(day??x.day))}${select('Starting period','period',shift.periods.map((s,i)=>({id:String(i+1),name:`${i+1} · ${s.start}–${s.end}`})),String(period??x.period))}${r.parts.map((part,i)=>select(`Room · ${name('teachers',part.teacher_id)}`,'room_'+i,part.room_ids.map(id=>({id,name:name('rooms',id)})),x.rooms[i])).join('')}</div>`,async f=>{state=await api('/move','POST',{revision:state.revision,occurrence:eid,day:+f.get('day'),period:+f.get('period'),rooms:r.parts.map((_,i)=>f.get('room_'+i))});await reload();toast('School timetable adapted. Your chosen session is locked.');},'Move & adapt school');
  $('#submit-dialog').disabled=x.locked||isStale();
  $('#lock-session').onclick=async()=>{try{state=await api('/lock','POST',{revision:state.revision,occurrence:eid,locked:!x.locked});$('#editor').close();await reload();await render();toast(x.locked?'Session unlocked.':'Session locked for regeneration.');}catch(e){$('#form-error').textContent=e.message;$('#form-error').hidden=false;}};
}
async function renderVersions(){
  const versions=await api('/versions');
  $('#main').innerHTML=heading('Every version, preserved.','Saved snapshots keep their original school inputs and timetable.',button('Save current draft','version','primary'))+`<section class="panel table-scroll"><table class="data-table"><thead><tr><th>Version</th><th>Created</th><th>Status</th><th></th></tr></thead><tbody>${versions.map(v=>`<tr><td><strong>${esc(v.name)}</strong><small>Version ${v.id}</small></td><td>${esc(new Date(v.created).toLocaleString())}</td><td><span class="badge ${v.kind==='published'?'':'grey'}">${v.id===state.published_id?'Current published':v.kind}</span></td><td><div class="actions"><a class="button small" href="/api/export/timetable?vid=${v.id}">CSV</a><button class="button small" data-version-download="${v.id}">Snapshot JSON</button><button class="button small" data-restore="${v.id}">Restore as draft</button></div></td></tr>`).join('')}</tbody></table>${!versions.length?'<div class="empty">Generate a timetable and save your first version.</div>':''}</section><section class="panel"><div class="panel-head"><h3>Recent activity</h3></div><div class="panel-body">${state.activity.slice(-12).reverse().map(a=>`<div class="check-row"><span class="checkmark">·</span><div>${esc(a.text)}<small>${esc(new Date(a.at).toLocaleString())}</small></div></div>`).join('')}</div></section>`;
}
function saveVersion(publish=false){
  if(!state.draft){toast('Generate a timetable first.');return;}
  dialog(publish?'Publish a timetable snapshot':'Save timetable version',field('Version name','name',`${state.project.school.year} · ${publish?'Published':'Draft'} ${new Date().toLocaleDateString()}`,'text','','required')+`<p class="help">${publish?'Creates an immutable published snapshot on this computer. It does not send messages or upload anything. Policy warnings remain attached to the snapshot.':'Preserves this timetable together with its input data. Later changes will not alter this version.'}</p>`,async f=>{state=await api(publish?'/publish':'/versions','POST',{revision:state.revision,name:f.get('name')});await reload();toast(publish?'Published snapshot saved locally.':'Version saved.');},publish?'Publish snapshot':'Save version');
}
async function renderDocument(){
  const data=await api('/'+page);
  if(page==='stages'){
    const lines=data.text.split('\n').filter(l=>/^\| \d\./.test(l));
    $('#main').innerHTML=heading('Project stages','A record of completed work, verification and the next milestones.')+`<section class="panel">${lines.map((line,i)=>{const v=line.split('|').map(x=>x.trim());return `<div class="stage-row"><span class="stage-number">${i+1}</span><div><strong>${esc(v[1].replace(/^\d\. /,''))}</strong><small>${esc(v[3])}</small></div><span class="badge ${v[2].startsWith('Complete')?'':v[2]==='In progress'?'blue':'grey'}">${esc(v[2])}</span></div>`;}).join('')}</section><details class="panel panel-body"><summary>Full project log</summary><pre class="doc">${esc(data.text)}</pre></details>`;
  }else{
    const text=esc(data.text).replace(/\[([^\]]+)\]\((https:\/\/[^\s)]+)\)/g,'<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    $('#main').innerHTML=heading('Research behind the timetable','Official sources, school decisions and the limits of what has been verified.')+`<section class="panel panel-body"><div class="doc">${text}</div></section>`;
  }
}
function download(filename,data){const u=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
async function removeEntity(value){
  const [kind,eid]=value.split(':'),x=entity(kind,eid);
  dialog('Delete '+x.name,`<p class="help">The application will reject this change if other school records still reference it. Saved timetable versions remain available.</p>`,async()=>{const p=clone(state.project);p[kind]=p[kind].filter(v=>v.id!==eid);await saveProject(p);},'Delete record');
}
document.addEventListener('click',async e=>{
  const b=e.target.closest('button,a');if(!b)return;
  try{
    if(b.dataset.allocation){const p=clone(state.project),t=p.teachers.find(t=>t.id===b.dataset.allocation);dialog('Approved hours · '+t.name,field('Approved weekly teaching periods','hours',t.assigned_weekly??'','number','Leave blank if not yet supplied.','min="0" max="120"'),async f=>{t.assigned_weekly=f.get('hours')===''?null:Number(f.get('hours'));await saveProject(p);});}
    if(b.dataset.page){page=b.dataset.page;if(b.dataset.resource)resource=b.dataset.resource;report=null;await render();}
    if(b.dataset.resource){resource=b.dataset.resource;renderResources();}
    if(b.dataset.req)editRequirement(b.dataset.req);
    if(b.dataset.ruleEdit)editRule(b.dataset.ruleEdit);
    if(b.dataset.ruleToggle){const p=clone(state.project),r=p.rules.find(r=>r.id===b.dataset.ruleToggle);r.enabled=!r.enabled;await saveProject(p);await render();}
    if(b.dataset.entity)editEntity(b.dataset.entity);
    if(b.dataset.delete)await removeEntity(b.dataset.delete);
    if(b.dataset.session)editSession(b.dataset.session);
    if(b.dataset.restore)dialog('Restore version '+b.dataset.restore,'<p class="help">This replaces current working inputs and the draft with the saved snapshot. Save your current version first if you want to preserve it. The published version is unchanged.</p>',async()=>{state=await api('/versions/'+b.dataset.restore+'/restore','POST',{revision:state.revision});await reload();toast('Restored as a working draft.');},'Restore as draft');
    if(b.dataset.versionDownload)download('maktab-version-'+b.dataset.versionDownload+'.json',(await api('/versions/'+b.dataset.versionDownload)).payload);
    if(b.dataset.action){e.preventDefault();const a=b.dataset.action;
      if(a==='generate')await generate();
      if(a==='rules'||a==='research'){page=a;await render();}
      if(a==='add-req')editRequirement();
      if(a==='teaching-csv')importTeaching();
      if(a==='add-rule')editRule();
      if(a==='add-resource')editEntity();
      if(a==='version'||a==='publish')saveVersion(a==='publish');
      if(a==='print')window.print();
      if(a==='export'){if(!state.draft||isStale()){toast('Generate a current timetable before exporting.');return;}location.href='/api/export/timetable';}
      if(a==='export-project')location.href='/api/export/project';
      if(a==='import')$('#import-file').click();
    }
  }catch(err){toast(err.message);}
});
$('#import-file').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>5_000_000)throw Error('Project file must be under 5 MB.');const raw=JSON.parse(await file.text()),data=raw.project||raw;dialog('Import school project',`<p class="help">Replace current school inputs with <strong>${esc(file.name)}</strong>? The server validates all references and rules. Existing timetable versions are retained.</p>`,async()=>{await saveProject(data);},'Validate and import');}catch(err){toast(err.message);}finally{e.target.value='';}};
$('#settings-btn').onclick=editSettings;$('#close-dialog').onclick=$('#cancel-dialog').onclick=()=>$('#editor').close();
document.addEventListener('DOMContentLoaded',()=>reload().then(render).catch(e=>{$('#main').innerHTML=`<div class="error">Could not load the workspace: ${esc(e.message)}</div>`;}));
