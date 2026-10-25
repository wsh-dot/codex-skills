import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';
const dir=path.resolve(process.argv[2]);
const d=JSON.parse(await fs.readFile(path.join(dir,'data.json'),'utf8'));
const wb=Workbook.create();
const navy='#234563',ink='#173653',green='#EDF4E8',blue='#EEF6FC';
const col=i=>{let s='';for(i++;i;i=Math.floor((i-1)/26))s=String.fromCharCode(65+(i-1)%26)+s;return s;};
const literal=x=>typeof x==='string'&&x.startsWith('=')?"'"+x:x;
function sheet(name,title,subtitle,headers,rows,widths){
 const s=wb.worksheets.add(name),end=col(headers.length-1),n=rows.length+4;
 s.showGridLines=false;s.tabColor=navy;
 s.getRange(`A1:${end}${n}`).format={font:{name:'Microsoft YaHei',size:10,color:ink},verticalAlignment:'center',rowHeight:24};
 const titleEnd=col(Math.min(headers.length-1,7));
 s.mergeCells(`A1:${titleEnd}1`);s.getRange('A1').values=[[title]];s.getRange('A1').format.font={bold:true,size:15,color:ink};s.getRange(`A1:${end}1`).format.rowHeight=30;
 s.mergeCells(`A2:${titleEnd}2`);s.getRange('A2').values=[[subtitle]];s.getRange('A2').format.font={size:10,color:'#61778B'};s.getRange(`A2:${end}2`).format.rowHeight=25;
 s.getRange(`A4:${end}4`).values=[headers];s.getRange(`A4:${end}4`).format={fill:navy,font:{color:'#FFFFFF',bold:true},rowHeight:32,horizontalAlignment:'center'};
 if(rows.length)s.getRange(`A5:${end}${n}`).values=rows.map(r=>r.map(literal));
 for(let i=0;i<widths.length;i++)s.getRange(`${col(i)}1:${col(i)}${n}`).format.columnWidth=widths[i];
 s.freezePanes.freezeRows(4);
 return s;
}
const tree=sheet('树结构',d.title,'项目、工程、分部、定额及主材和设备明细；按原层级顺序排列；金额单位：元',d.headers,d.rows,[9,26,26,7,11,25,60,10,46,17,17,17,17,17,18,18,18,19,62,20]);
if(!d.isComplete)tree.getRange('A2').values=[[d.partialSubtitle]];
tree.getRange(`J5:R${d.rows.length+4}`).setNumberFormat('#,##0.00######');
tree.getRange(`B5:C${d.rows.length+4}`).setNumberFormat('@');
tree.getRange(`F5:I${d.rows.length+4}`).format.horizontalAlignment='left';
tree.getRange(`G5:I${d.rows.length+4}`).format.wrapText=true;
for(let i=0;i<d.rows.length;i++){
 const r=d.rows[i],row=i+5;let fill=null;
 if(r[4]==='项目')fill='#D8E5F0';else if(r[4]==='项目分组')fill='#E4EDF5';else if(r[4]==='工程'||r[4]==='分部')fill=green;else if(r[19]==='ZCSpend')fill=blue;
 if(fill)tree.getRange(`A${row}:T${row}`).format.fill=fill;
 if(r[19].includes('未读取'))tree.getRange(`A${row}:T${row}`).format={fill:'#FFF0D6',font:{color:'#9C4F00'}};
 if(['项目','项目分组','工程','分部'].includes(r[4])){tree.getRange(`E${row}:G${row}`).format.font.bold=true;}
 const wide=t=>[...(t||'')].reduce((n,c)=>n+(c.charCodeAt(0)>255?2:1),0);
 const lines=Math.max(Math.ceil(wide(r[6])/59),Math.ceil(wide(r[8])/45),1);
 if(lines>1)tree.getRange(`A${row}:T${row}`).format.rowHeight=Math.min(409,lines*16+8);
}
const sp=sheet('定额人材机','定额人材机耗量','按父层级编号关联树结构中的预算节点；耗量与定额耗量均保留源值',d.spendHeaders,d.spends,[9,32,24,65,12,19,19,64]);
if(d.spends.length){
sp.getRange(`F5:G${d.spends.length+4}`).setNumberFormat('#,##0.00######');
sp.getRange(`B5:B${d.spends.length+4}`).setNumberFormat('@');
}
const fee=sheet('项目其他费用','项目其他费用','按所属项目及原费用层级排列；保留源文件的编制费用、送审费用与计算式；金额单位：元',d.feeHeaders,d.fees,[9,24,62,26,26,8,13,18,58,22,15,72,22,22,22,50]);
if(d.fees.length){
fee.getRange(`J5:O${d.fees.length+4}`).setNumberFormat('#,##0.000000');
fee.getRange(`L5:L${d.fees.length+4}`).setNumberFormat('@');
fee.getRange(`I5:L${d.fees.length+4}`).format.wrapText=true;
}
for(let i=0;i<d.fees.length;i++){
 const r=d.fees[i],row=i+5;
 if(r[6]==='费用分部'){fee.getRange(`A${row}:P${row}`).format.fill=green;fee.getRange(`G${row}:I${row}`).format.font.bold=true;}
 const lines=Math.max(Math.ceil((r[11]||'').length/70),Math.ceil((r[8]||'').length/28),1);
 if(lines>1)fee.getRange(`A${row}:P${row}`).format.rowHeight=Math.min(409,lines*16+8);
}
const checkRows=d.checks.map(r=>[...r,r[8]===null?'明细未读取：见来源与核对':'已读取']);
const check=sheet('工程核对','工程数据与造价核对',d.isComplete?'差额为预算树根造价减项目目录造价；源数据差额保留；金额单位：元':d.partialSubtitle,[...d.checkHeaders,'读取状态'],checkRows,[25,28,64,18,20,18,20,23,23,19,54,20,20,44]);
check.getRange(`H5:J${d.checks.length+4}`).setNumberFormat('#,##0.000');
for(let i=0;i<d.checks.length;i++){
 const row=i+5;
 if(d.checks[i][8]!==null)check.getRange(`J${row}`).formulas=[[`=I${row}-H${row}`]];
 else check.getRange(`A${row}:N${row}`).format={fill:'#FFF0D6',font:{color:'#9C4F00'}};
 if(Math.abs(d.checks[i][9])>0.00001)check.getRange(`H${row}:J${row}`).format={fill:'#FFF0D6',font:{color:'#9C4F00',bold:true}};
}
const source=sheet('来源与核对','来源与读取说明','数据来源：用户提供的 ecpt5 项目文件；按工程原层级导出，保留源值。', ['项目','值'],d.summary,[36,145]);
source.getRange(`B5:B${d.summary.length+4}`).format.wrapText=true;
source.getRange(`B5:B${d.summary.length+4}`).setNumberFormat('#,##0.000');
for(let i=0;i<d.summary.length;i++){
 if(typeof d.summary[i][1]==='number'&&Number.isInteger(d.summary[i][1]))source.getRange(`B${i+5}`).setNumberFormat('#,##0');
 if(typeof d.summary[i][1]==='string'){
  const wide=[...d.summary[i][1]].reduce((n,c)=>n+(c.charCodeAt(0)>255?2:1),0);
  const lines=Math.ceil(wide/143);
  if(lines>1)source.getRange(`A${i+5}:B${i+5}`).format.rowHeight=Math.min(409,lines*16+10);
 }
}
wb.recalculate();
console.log('AUTHORED',d.outputName);
const inspect=await wb.inspect({kind:'table',range:'树结构!A4:N12',include:'values,formulas',tableMaxRows:9,tableMaxCols:14,maxChars:3000});
await fs.writeFile(path.join(dir,'inspection.ndjson'),inspect.ndjson);
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},maxChars:1800});
console.log(errors.ndjson);
for(const [name,range] of [['树结构','A1:N17'],['定额人材机','A1:H14'],['项目其他费用','A1:K14'],['工程核对','A1:J12'],['来源与核对','A1:B17']]){
 const blob=await wb.render({sheetName:name,range,scale:1,format:'png'});
 await fs.writeFile(path.join(dir,`${name}_preview.png`),new Uint8Array(await blob.arrayBuffer()));
 console.log('Rendered',name);
}
const output=await SpreadsheetFile.exportXlsx(wb);
const target=path.join(dir,'..',d.outputName);
await output.save(target);
console.log('EXPORTED',target);
await fs.writeFile(path.join(dir,'authoring_complete.json'),JSON.stringify({target,rows:d.rows.length}));
