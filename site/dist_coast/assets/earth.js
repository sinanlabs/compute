
(function(){var cv=document.getElementById("gl");if(!cv)return;var gl=cv.getContext("webgl2",{alpha:true,antialias:false,premultipliedAlpha:true});if(!gl){cv.remove();return;}
var reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
var vs="#version 300 es\nin vec2 p;void main(){gl_Position=vec4(p,0.,1.);}";
var fs=["#version 300 es","precision highp float;out vec4 O;uniform vec2 R;uniform float T;uniform vec2 M;uniform float S;uniform float HC;uniform sampler2D D;uniform sampler2D N;uniform sampler2D C;",
"mat2 rot(float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c);}",
"vec2 isph(vec3 ro,vec3 rd,float r){float b=dot(ro,rd);float c=dot(ro,ro)-r*r;float h=b*b-c;if(h<0.)return vec2(-1.);h=sqrt(h);return vec2(-b-h,-b+h);}",
"float hash(vec3 p){p=fract(p*.3183099+.1);p*=17.;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}",
"float noise(vec3 x){vec3 i=floor(x),f=fract(x);f=f*f*(3.-2.*f);return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);}",
"float fbm(vec3 p){float a=.5,s=0.;for(int i=0;i<6;i++){s+=a*noise(p);p=p*2.07+vec3(1.7,9.2,3.1);a*=.52;}return s;}",
"vec3 geo(vec3 n){vec3 q=n;q.xy*=rot(-.41);q.xz*=rot(-(T*.012+S)-2.6);return q;}",
"vec2 equi(vec3 q){return vec2(atan(q.z,q.x)/6.28318+.5,asin(clamp(q.y,-1.,1.))/3.14159+.5);}",
"float clouds(vec3 q){if(HC>.5){vec2 uv=equi(q);uv.x+=T*.0015;float c=texture(C,uv).r;return smoothstep(.08,.85,c);}",
" vec3 w=q*2.2;w.xz*=rot(T*.004);vec3 warp=vec3(fbm(w*2.4),fbm(w*2.4+vec3(5.2,1.3,7.7)),0.)*.9;float f=fbm(w*1.5+warp);float band=.85+.15*sin(q.y*9.);return smoothstep(.47,.74,f*band+.02);}",
"void main(){vec2 uv=(gl_FragCoord.xy-.5*R)/R.y;",
" float pitch=.78+(M.y-.5)*.05,yaw=(M.x-.5)*.06,roll=.10;",
" vec3 ro=vec3(0.,0.,1.36);vec3 f=vec3(0.,sin(pitch),-cos(pitch));f.xz*=rot(yaw);",
" vec3 rgt=normalize(cross(f,vec3(0.,1.,0.)));vec3 up=cross(rgt,f);mat2 rr=rot(roll);vec2 u2=rr*uv;",
" vec3 rd=normalize(f*1.55+u2.x*rgt+u2.y*up);",
" vec3 L=normalize(vec3(-.45,.5,.8));",
" float RA=1.09;vec2 ta=isph(ro,rd,RA);if(ta.y<0.){O=vec4(0.);return;}vec2 tg=isph(ro,rd,1.0);bool ground=tg.x>0.;",
" float t0=max(ta.x,0.),t1=ground?tg.x:ta.y;",
" vec3 col=vec3(0.);float alpha=0.;",
" float bcl=dot(-ro,rd);float dc=length(ro+rd*bcl);float pxs=bcl/(R.y*1.55);float cov=clamp((1.0-dc)/pxs+.5,0.,1.);",
" if(ground){vec3 p=ro+rd*tg.x;vec3 n=p;vec3 q=geo(n);vec2 tuv=equi(q);",
"  vec3 dpx=dFdx(q),dpy=dFdy(q);vec2 gx=vec2(length(dpx)/6.28318,length(dpx)/3.14159),gy=vec2(length(dpy)/6.28318,length(dpy)/3.14159);",
"  vec3 day=pow(textureGrad(D,tuv,gx,gy).rgb,vec3(2.2));vec3 night=pow(textureGrad(N,tuv,gx,gy).rgb,vec3(2.2));",
"  float ndl=dot(n,L);float lit=clamp(ndl,0.,1.);float dayl=smoothstep(-.06,.2,ndl);",
"  float ocean=smoothstep(.015,.12,day.b-max(day.r,day.g));",
"  vec3 hv=normalize(L-rd);float spec=pow(clamp(dot(n,hv),0.,1.),220.)*ocean*dayl;float sheen=pow(clamp(dot(n,hv),0.,1.),10.)*ocean*dayl*.07;",
"  float fresO=pow(1.-clamp(dot(n,-rd),0.,1.),4.)*ocean;",
"  float cl=clouds(q);vec3 qs=geo(normalize(n+L*.03));float cls=clouds(qs);float clsh=cls;",
"  float cshade=clamp(1.+(cls-cl)*1.6,.55,1.35);",
"  vec3 g=mix(day,day*vec3(.55,.95,1.55)+vec3(0.,.02,.09),ocean)*(1.-clsh*.55);",
"  vec3 dayc=g*(lit*2.1+.02)+vec3(1.,.95,.85)*spec*1.8+vec3(.6,.75,1.)*sheen*2.+vec3(.35,.55,1.)*fresO*lit*.35;",
"  float twi=smoothstep(.22,0.,ndl)*smoothstep(-.12,.02,ndl);dayc+=vec3(1.,.45,.15)*twi*.12*(1.-cl);",
"  vec3 cloudc=mix(vec3(.62,.7,.9),vec3(1.),cshade*lit)*(lit*1.95+.03);cloudc+=vec3(1.,.5,.2)*twi*.25;",
"  float clv=cl*cl*.85+cl*.15;dayc=mix(dayc,cloudc,clv);",
"  vec3 nightc=night*vec3(1.,.72,.42)*2.4*(1.-cl*.85)+g*vec3(.5,.62,1.)*.028+vec3(.5,.6,1.)*cl*.02;",
"  col=dayc*dayl+nightc*(1.-dayl);alpha=1.;}",
" const int NS=14;float st=(t1-t0)/float(NS);vec3 sc=vec3(0.);float od=0.;",
" vec3 ray=vec3(.22,.48,1.0);vec3 low=vec3(.78,.86,1.);vec3 warm=vec3(1.,.42,.16);float mie=pow(clamp(dot(rd,L),0.,1.),14.)*.35;",
" for(int i=0;i<NS;i++){float t=t0+st*(float(i)+.5);vec3 p=ro+rd*t;float hgt=length(p)-1.;float dens=exp(-hgt/.024)*st;",
"  float mu=dot(normalize(p),L);float sun=clamp(mu*1.4+.32,0.,1.);sun*=sun;od+=dens;float tw=smoothstep(.35,-.05,mu)*smoothstep(-.3,-.02,mu);",
"  vec3 c=mix(ray,low,exp(-hgt/.011)*.7);c=mix(c,warm,tw*.55);sc+=dens*exp(-od*7.)*sun*(c+mie*vec3(1.,.9,.8));}",
" vec3 scat=sc*30.;float tr=exp(-od*4.);",
" float aA=clamp(1.-exp(-od*9.),0.,1.)*clamp(length(scat)*4.,0.,1.);",
" if(ground){vec3 gc=col*mix(1.,tr,.6)+scat;col=mix(scat,gc,cov);alpha=mix(aA,1.,cov);}else{col=scat;alpha=aA;}",
" col=1.-exp(-col*1.1);col=pow(col,vec3(.4545));col=mix(col,col*col*(3.-2.*col),.25);",
" O=vec4(col*alpha,alpha);}"].join("\n");
function sh(t,s){var o=gl.createShader(t);gl.shaderSource(o,s);gl.compileShader(o);if(!gl.getShaderParameter(o,gl.COMPILE_STATUS)){console.warn(gl.getShaderInfoLog(o));}return o;}
var pr=gl.createProgram();gl.attachShader(pr,sh(gl.VERTEX_SHADER,vs));gl.attachShader(pr,sh(gl.FRAGMENT_SHADER,fs));gl.linkProgram(pr);if(!gl.getProgramParameter(pr,gl.LINK_STATUS)){console.warn(gl.getProgramInfoLog(pr));return;}gl.useProgram(pr);
var buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW);var pl=gl.getAttribLocation(pr,"p");gl.enableVertexAttribArray(pl);gl.vertexAttribPointer(pl,2,gl.FLOAT,false,0,0);
var U={};["R","T","M","S","HC","D","N","C"].forEach(function(k){U[k]=gl.getUniformLocation(pr,k);});gl.uniform1i(U.D,0);gl.uniform1i(U.N,1);gl.uniform1i(U.C,2);gl.uniform1f(U.HC,0);
var need=3,loaded=0,ready=false;function tex(unit,src,onl){var im=new Image();im.onload=function(){var t=gl.createTexture();gl.activeTexture(gl.TEXTURE0+unit);gl.bindTexture(gl.TEXTURE_2D,t);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGB,gl.RGB,gl.UNSIGNED_BYTE,im);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.REPEAT);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.generateMipmap(gl.TEXTURE_2D);var ext=gl.getExtension("EXT_texture_filter_anisotropic");if(ext)gl.texParameterf(gl.TEXTURE_2D,ext.TEXTURE_MAX_ANISOTROPY_EXT,Math.min(8,gl.getParameter(ext.MAX_TEXTURE_MAX_ANISOTROPY_EXT)));if(onl)onl();loaded++;if(loaded>=need)ready=true;};im.onerror=function(){loaded++;if(loaded>=need)ready=true;};im.src=src;}
tex(0,"/img/earth_day.jpg");tex(1,"/img/earth_night.jpg");tex(2,"/img/earth_cloud.jpg",function(){gl.uniform1f(U.HC,1);});
var mx=.5,my=.5,tx=.5,ty=.5,spin=0,vel=0,drag=null;addEventListener("pointermove",function(e){tx=e.clientX/innerWidth;ty=1-e.clientY/innerHeight;if(drag){var dx=e.clientX-drag.x;drag.x=e.clientX;vel=dx*.0035;spin+=vel;}});
cv.addEventListener("pointerdown",function(e){drag={x:e.clientX};cv.setPointerCapture(e.pointerId);});cv.addEventListener("pointerup",function(){drag=null;});cv.addEventListener("pointercancel",function(){drag=null;});
function size(){var b=cv.getBoundingClientRect();var s=Math.min(devicePixelRatio||1,1.5,1400/Math.max(1,b.width));cv.width=Math.max(2,b.width*s|0);cv.height=Math.max(2,b.height*s|0);gl.viewport(0,0,cv.width,cv.height);}size();addEventListener("resize",size);
var t0=performance.now(),vis=true;new IntersectionObserver(function(es){vis=es[0].isIntersecting;}).observe(cv);
function frame(t){if(vis&&ready){mx+=(tx-mx)*.05;my+=(ty-my)*.05;if(!drag){spin+=vel;vel*=.94;}gl.uniform2f(U.R,cv.width,cv.height);gl.uniform1f(U.T,reduce?0:(t-t0)/1000);gl.uniform2f(U.M,mx,my);gl.uniform1f(U.S,spin);gl.drawArrays(gl.TRIANGLE_STRIP,0,4);}requestAnimationFrame(frame);}requestAnimationFrame(frame);})();
/* 星空 */
(function(){var cv=document.getElementById("stars");if(!cv)return;var hero=cv.parentNode;var ctx=cv.getContext("2d");if(!ctx)return;var W,Hh,S=[];var reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
function size(){var b=hero.getBoundingClientRect(),d=Math.min(2,devicePixelRatio||1);W=b.width;Hh=b.height;cv.width=W*d;cv.height=Hh*d;ctx.setTransform(d,0,0,d,0,0);S=[];var n=Math.round(W*Hh/3800);for(var i=0;i<n;i++){S.push({x:Math.random(),y:Math.random(),z:.3+Math.random()*.7,s:.35+Math.random()*1.1,tw:Math.random()*6.28,sp:.6+Math.random()*1.6,c:Math.random()<.12?"200,215,255":Math.random()<.06?"255,225,190":"255,255,255"});}}
size();addEventListener("resize",size);var mx=0,my=0;addEventListener("pointermove",function(e){mx=e.clientX/innerWidth-.5;my=e.clientY/innerHeight-.5;});var px=0,py=0;
function frame(t){px+=(mx-px)*.04;py+=(my-py)*.04;ctx.clearRect(0,0,W,Hh);var tm=t/1000;for(var i=0;i<S.length;i++){var s=S[i];var x=s.x*W-px*14*s.z,y=s.y*Hh-py*10*s.z;var a=(.35+.65*(.5+.5*Math.sin(tm*s.sp+s.tw)))*s.z;ctx.fillStyle="rgba("+s.c+","+a.toFixed(3)+")";ctx.beginPath();ctx.arc(x,y,s.s,0,6.283);ctx.fill();if(s.s>1.25&&a>.8){ctx.fillStyle="rgba("+s.c+","+(a*.35).toFixed(3)+")";ctx.fillRect(x-s.s*3,y-.4,s.s*6,.8);ctx.fillRect(x-.4,y-s.s*3,.8,s.s*6);}}if(!reduce)requestAnimationFrame(frame);}
requestAnimationFrame(frame);})();
