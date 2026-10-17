// Dependency-free build for GitHub Pages and Cloudflare Pages.
const fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'..'),dist=path.join(root,'dist');
fs.mkdirSync(dist,{recursive:true});
fs.cpSync(path.join(root,'site'),dist,{recursive:true,force:true});
fs.copyFileSync(path.join(root,'src','icons.svg'),path.join(dist,'icons.svg'));
fs.mkdirSync(path.join(dist,'assets'),{recursive:true});
const modules=fs.readdirSync(path.join(root,'src','js')).filter(x=>x.endsWith('.js')).sort();
for(const mod of modules){
 let code=fs.readFileSync(path.join(root,'src','js',mod),'utf8');
 code=code.replaceAll("'/feed/", "'./feed/").replaceAll('"/feed/', '"./feed/');
 fs.writeFileSync(path.join(dist,'assets',mod),code);
}
let html=fs.readFileSync(path.join(root,'src','index.html'),'utf8');
const assets=['<link rel="stylesheet" href="./app.css">',...['data-1.js','data-2.js','data-3.js'].map(x=>`<script src="./${x}" defer></script>`),...modules.map(x=>`<script src="./assets/${x}" defer></script>`)].join('\n');
html=html.replace('<!--ASSETS-->',assets).replace(/(href|src)="\/(?!\/)/g,'$1="./');
fs.writeFileSync(path.join(dist,'index.html'),html);
fs.writeFileSync(path.join(dist,'.nojekyll'),'');
console.log('Built static site:',modules.length,'JS modules');
