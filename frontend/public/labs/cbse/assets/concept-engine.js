/* Whitelisted mathematical models: no expression evaluation, HTML or remote resources. */
(function(){'use strict';
  var config=null, values={}, answers={}, rows=[], st=LK.setupCanvas(document.getElementById('cv'));
  var channel=new URLSearchParams(location.search).get('channel');
  var engines={
    linear:{parameters:[['Slope m',-5,5,.1,1],['Intercept b',-10,10,.5,0]],formula:'y = mx + b',compute:function(v,x){return v[0]*x+v[1];},read:function(v){return 'At x = 2, y = '+(2*v[0]+v[1]).toFixed(2);}},
    projectile:{parameters:[['Speed (m/s)',1,60,1,20],['Angle (degrees)',5,85,1,45],['Gravity (m/s²)',1,25,.1,9.8]],formula:'Ideal projectile: no air resistance. y = x tan θ − gx² / (2u² cos² θ).',compute:function(v,x){var a=v[1]*Math.PI/180;return x*Math.tan(a)-v[2]*x*x/(2*v[0]*v[0]*Math.cos(a)**2);},read:function(v){return 'Range: '+(v[0]**2*Math.sin(2*v[1]*Math.PI/180)/v[2]).toFixed(2)+' m';}},
    pendulum:{parameters:[['Length (m)',.1,5,.1,1],['Gravity (m/s²)',1,25,.1,9.8]],formula:'Small-angle model: T = 2π√(L/g). Angle is shown in relative units.',compute:function(v,t){return Math.cos(Math.sqrt(v[1]/v[0])*t);},read:function(v){return 'Period: '+(2*Math.PI*Math.sqrt(v[0]/v[1])).toFixed(3)+' s';}},
    circuit:{parameters:[['Voltage (V)',0,24,.5,12],['Resistance (Ω)',1,100,1,10]],formula:'Ideal ohmic resistor: I = V/R; P = VI. Temperature effects are excluded.',compute:function(v,x){return x/v[1];},read:function(v){return 'Current: '+(v[0]/v[1]).toFixed(3)+' A · Power: '+(v[0]**2/v[1]).toFixed(2)+' W';}},
    gas:{parameters:[['Temperature (K)',100,600,10,300],['Volume (L)',1,30,.5,10],['Amount (mol)',.1,3,.1,1]],formula:'Ideal gas: P = nRT/V, R = 8.314 kPa·L/(mol·K). Not accurate near condensation.',compute:function(v,x){return v[2]*8.314*v[0]/Math.max(x,.1);},read:function(v){return 'Pressure: '+(v[2]*8.314*v[0]/v[1]).toFixed(2)+' kPa';}},
    wave:{parameters:[['Amplitude',.1,3,.1,1],['Frequency (Hz)',.1,5,.1,1],['Wave speed (m/s)',1,20,1,4]],formula:'Ideal sinusoidal wave: y = A sin(2πfx/v); λ = v/f.',compute:function(v,x){return v[0]*Math.sin(2*Math.PI*v[1]*x/v[2]);},read:function(v){return 'Wavelength: '+(v[2]/v[1]).toFixed(2)+' m';}}
  };
  function post(data){if(channel)parent.postMessage(Object.assign({type:'sasha-lab-trial',channel:channel},data),location.origin);}
  function renderControls(){
    var area=document.getElementById('controls');area.replaceChildren();rows=[];
    if(config.engine==='classification'){
      var groups=Array.from(new Set(config.cards.map(function(c){return c.group;})));
      config.cards.forEach(function(card,i){var row=document.createElement('div');row.className='lk-row';var label=document.createElement('label');label.textContent=card.label;label.htmlFor='card-'+i;
        var select=document.createElement('select');select.id=label.htmlFor;var blank=document.createElement('option');blank.textContent='Choose a group';blank.value='';select.appendChild(blank);
        groups.forEach(function(g){var option=document.createElement('option');option.textContent=g;option.value=g;select.appendChild(option);});
        select.value=answers[i]||'';select.addEventListener('change',function(){answers[i]=select.value;});row.append(label,select);area.appendChild(row);
      });
      var check=document.createElement('button');check.className='lk-btn';check.textContent='Check classification';check.addEventListener('click',function(){
        var correct=config.cards.filter(function(c,i){return answers[i]===c.group;}).length;
        document.getElementById('result').textContent=correct+' / '+config.cards.length+' matched. '+config.cards.filter(function(c,i){return answers[i]!==c.group;}).map(function(c){return c.label+': '+c.group+'. '+c.explanation;}).join(' ');
      });area.appendChild(check);return;
    }
    engines[config.engine].parameters.forEach(function(p,i){var row=document.createElement('div');row.className='lk-row';var label=document.createElement('label');label.textContent=p[0];label.htmlFor='parameter-'+i;
      var slider=document.createElement('input');slider.type='range';slider.id=label.htmlFor;slider.min=p[1];slider.max=p[2];slider.step=p[3];slider.value=values[i]??p[4];values[i]=Number(slider.value);
      var output=document.createElement('output');output.htmlFor=slider.id;output.textContent=slider.value;
      slider.addEventListener('input',function(){values[i]=Number(slider.value);output.textContent=slider.value;update();});row.append(label,slider,output);area.appendChild(row);rows.push({label:p[0],slider:slider});
    });update();
  }
  function update(){if(config&&engines[config.engine])document.getElementById('result').textContent=engines[config.engine].read(values);}
  st.draw=function(s){
    var ctx=s.ctx,w=s.w,h=s.h;ctx.clearRect(0,0,w,h);ctx.fillStyle='#fcfaf7';ctx.fillRect(0,0,w,h);
    if(!config){ctx.fillStyle='#314155';ctx.font='18px sans-serif';ctx.fillText('Open a concept lab from the LMS.',25,50);return;}
    if(config.engine==='classification'){
      ctx.font='16px sans-serif';var cardW=Math.max(120,(w-60)/3);
      config.cards.forEach(function(c,i){var x=20+(i%3)*cardW,y=25+Math.floor(i/3)*65;ctx.fillStyle=answers[i]===c.group?'#d1fae5':answers[i]?'#ffedd5':'#e7edf3';ctx.fillRect(x,y,cardW-10,54);ctx.fillStyle='#1e3446';ctx.fillText(c.label.slice(0,21),x+9,y+23);ctx.font='12px sans-serif';ctx.fillText(answers[i]||'Choose a group →',x+9,y+43);ctx.font='16px sans-serif';});return;
    }
    var e=engines[config.engine], xmin=config.engine==='linear'?-10:0,xmax=config.engine==='gas'?30:config.engine==='circuit'?24:10;
    if(config.engine==='projectile')xmax=Math.max(5,values[0]**2*Math.sin(2*values[1]*Math.PI/180)/values[2]*1.1);
    var points=Array.from({length:201},function(_,i){var x=xmin+(xmax-xmin)*i/200;return[x,e.compute(values,x)];});
    var ys=points.map(function(p){return p[1];}).filter(Number.isFinite),ymin=Math.min(0,...ys),ymax=Math.max(1,...ys);if(config.engine==='gas')ymax=Math.max(100,e.compute(values,1));
    var X=function(x){return 58+(x-xmin)/(xmax-xmin)*(w-85);},Y=function(y){return h-55-(y-ymin)/(ymax-ymin)*(h-90);};
    ctx.strokeStyle='#e2e8f0';ctx.font='12px sans-serif';ctx.fillStyle='#526277';
    for(var i=0;i<=5;i++){var x=xmin+(xmax-xmin)*i/5,y=ymin+(ymax-ymin)*i/5;ctx.beginPath();ctx.moveTo(X(x),30);ctx.lineTo(X(x),h-55);ctx.stroke();ctx.fillText(x.toFixed(1),X(x)-10,h-32);ctx.beginPath();ctx.moveTo(58,Y(y));ctx.lineTo(w-27,Y(y));ctx.stroke();ctx.fillText(y.toFixed(1),6,Y(y)+4);}
    ctx.save();ctx.beginPath();ctx.rect(58,25,w-85,h-80);ctx.clip();ctx.strokeStyle='#c2410c';ctx.lineWidth=3;ctx.beginPath();points.forEach(function(p,i){if(i===0)ctx.moveTo(X(p[0]),Y(p[1]));else ctx.lineTo(X(p[0]),Y(p[1]));});ctx.stroke();ctx.restore();
    ctx.fillStyle='#243449';ctx.font='14px sans-serif';var axes={linear:'x →     y ↑',projectile:'Horizontal distance (m) →     Height (m) ↑',pendulum:'Time (s) →     Relative angle ↑',circuit:'Voltage (V) →     Current (A) ↑',gas:'Volume (L) →     Pressure (kPa) ↑',wave:'Position (m) →     Displacement ↑'};ctx.fillText(axes[config.engine],58,18);
  };
  document.getElementById('capture').addEventListener('click',function(){if(!config)return;var trial={engine:config.engine,time:new Date().toISOString(),result:document.getElementById('result').textContent};rows.forEach(function(r){trial[r.label]=Number(r.slider.value);});if(config.engine==='classification')trial.answers=JSON.stringify(answers);post({trial:trial});document.getElementById('capture').textContent='Trial sent to notebook';setTimeout(function(){document.getElementById('capture').textContent='Capture trial';},1500);});
  document.getElementById('reset').addEventListener('click',function(){if(!config)return;values={};answers={};renderControls();document.getElementById('result').textContent='';update();});
  window.addEventListener('message',function(event){
    if(event.source!==parent||event.origin!==location.origin||event.data?.type!=='sasha-lab-config'||event.data.channel!==channel)return;
    var c=event.data.config;if(!c||(!engines[c.engine]&&c.engine!=='classification'))return;
    config=c;values={};answers={};document.getElementById('capture').hidden=!event.data.canCapture;document.getElementById('title').textContent=String(event.data.title||'Concept lab');document.getElementById('objective').textContent=c.objective;
    document.getElementById('prediction').textContent=c.prediction;document.getElementById('explanation').textContent=(engines[c.engine]?.formula||'Compare classifications and explain the grouping rule.')+' '+c.explanation;
    var steps=document.getElementById('steps');steps.replaceChildren();c.investigation.forEach(function(text){var li=document.createElement('li');li.textContent=text;steps.appendChild(li);});renderControls();
  });
  parent.postMessage({type:'sasha-lab-ready',channel:channel},location.origin);
})();
