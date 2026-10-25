from pathlib import Path
import json, collections, re, xml.etree.ElementTree as ET
def key(code):
    if not isinstance(code,str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*",code):raise ValueError("INVALID_HIERARCHY: "+str(code))
    return tuple(int(s) for s in code.split('.'))
def clean(v): return None if v=='' else v
def num(e,k): return float(e.get(k) or '0')
TYPES={10:'人工',20:'材料',30:'机械',40:'主材',50:'设备',60:'仪表'}
HEADERS=['序号','层级编号','父层级编号','层级','标识','编号','名称','单位','工程量计算式','工程量','单价','人工单价','材料单价','机械单价','主材费','设备费','基价合计','造价合计','数据库对象ID','来源类型']

def local_rows(db):
    def obj(ref):
        assert ref and ref['ref'] in db,ref
        return db[ref['ref']]
    def fields(ref): return obj(ref)['fields']
    cfs=[o for o in db.values() if o['type'].endswith('.CostFile')]
    assert len(cfs)==1,len(cfs)
    cf=cfs[0]
    nodes=[obj(x) for x in fields(cf['fields']['zmItemList'])['items']]
    nodes.sort(key=lambda o:key(o['fields']['BSID']))
    codes={o['fields']['BSID'] for o in nodes}
    assert len(codes)==len(nodes)
    assert all(c=='1' or c.rsplit('.',1)[0] in codes for c in codes)
    rows=[];spends=[];zc_ids=[]
    for o in nodes:
        a=o['fields'];c=a['BSID'];kind=o['type'].split('.')[-1]
        mark=a.get('mark');no=a.get('no');name=a.get('name');unit=a.get('unit')
        if kind=='ZMGljEntity':
            ed=fields(a['edrcj']);no=ed.get('sysCode');name=ed.get('name');unit=ed.get('unit');mark=TYPES.get(ed.get('gljType'),mark)
        rows.append([len(rows)+1,c,c.rsplit('.',1)[0] if '.' in c else None,len(c.split('.')),mark,clean(no),clean(name),clean(unit),clean(a.get('gclFormula')),
            a.get('gcl'),a.get('unitPrice'),a.get('rgFee'),a.get('clFee'),a.get('jxFee'),a.get('zcFee'),a.get('sbFee'),a.get('totalPrices'),a.get('zzj'),o['id'],kind])
        for ref in a.get('zcSpend') or []:
            z=obj(ref);zf=z['fields'];ed=fields(zf['edrcj']);t=TYPES.get(ed.get('gljType'),'主材/设备');amount=zf.get('totalPrice')
            rows.append([len(rows)+1,None,c,len(c.split('.'))+1,t,ed.get('sysCode'),ed.get('name'),ed.get('unit'),None,zf.get('actSpend'),zf.get('scPrice'),None,None,None,
                amount if t=='主材' else None,amount if t=='设备' else None,None,amount,z['id'],'ZCSpend'])
            zc_ids.append(z['id'])
        for ref in sorted(a.get('rcjSpend') or [],key=lambda ref:(fields(fields(ref)['edrcj']).get('sysCode') or '',ref['ref'])):
            s=obj(ref);sf=s['fields'];ed=fields(sf['edrcj'])
            spends.append([len(spends)+1,c,ed.get('sysCode'),ed.get('name'),ed.get('unit'),sf.get('spend'),sf.get('deSpend'),s['id']])
    assert len(zc_ids)==len(set(zc_ids))
    return cf,rows,spends,nodes

def build_model(work, source, failures, output_name):
    raw=(work/'arr.xml').read_bytes()
    declared=re.search(br'encoding\s*=\s*[\'"]([^\'"]+)',raw[:180],re.I)
    encoding=declared.group(1).decode('ascii') if declared else 'utf-8-sig'
    if encoding.lower() in ('gbk','gb2312'):encoding='gb18030'
    text=raw.decode(encoding)
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():raise ValueError('UNSUPPORTED_XML_ENTITY')
    root=ET.fromstring(text)
    projects=sorted([e for e in root if e.tag in ('ProjInfoEntity','EditorCellEntity')],key=lambda e:key(e.get('orderCode')))
    if not projects:raise ValueError('PROJECT_DIRECTORY_MISSING')
    roots=[e for e in projects if '.' not in e.get('orderCode','')]
    if len(roots)!=1:raise ValueError('EXPECTED_ONE_PROJECT_ROOT')
    top_project=roots[0]
    xml_by_id={e.get('id'):e for e in root if e.get('id')}
    expected={e.get('costFileId') for e in projects if e.tag=='EditorCellEntity'}
    dbs={}
    for p in work.glob('*.ecd.jsonl'):
        try:
            objs=[json.loads(l) for l in p.read_text(encoding='utf-8').splitlines()]
            dbs[p.name.removesuffix('.ecd.jsonl')]={o['id']:o for o in objs}
        except Exception as exc:failures[p.name.removesuffix('.ecd.jsonl')]='INVALID_OBJECT_DUMP: '+str(exc)
    if set(dbs)-expected:raise ValueError('UNREFERENCED_DATABASES: '+','.join(set(dbs)-expected))
    rows=[];spends=[];checks=[];mapping=[];unreadable=[];costfile_diffs=[];node_count=zc_count=0
    for e in projects:
        prefix=e.get('orderCode')
        if e.tag=='ProjInfoEntity':
            rows.append([len(rows)+1,prefix,prefix.rsplit('.',1)[0] if '.' in prefix else None,len(prefix.split('.')),'项目' if e is top_project else '项目分组',e.get('sysCode'),e.get('name'),clean(e.get('unit')),None,None,None,None,None,None,num(e,'bzzcfee'),num(e,'bzsbfee'),None,num(e,'bzcost'),e.get('id'),'ProjInfoEntity'])
            continue
        uid=e.get('costFileId')
        try:
            if uid not in dbs:raise ValueError(failures.get(uid,'DATABASE_ENTRY_MISSING'))
            cf,local,local_spends,nodes=local_rows(dbs[uid]);c=cf['fields']
            tops=[o for o in nodes if o['fields']['BSID']=='1']
            if len(tops)!=1:raise ValueError('EXPECTED_ONE_BUDGET_ROOT')
            top=tops[0]
        except Exception as exc:
            reason=str(exc) or type(exc).__name__
            unreadable.append({'project':prefix,'name':e.get('name'),'database':uid,'reason':reason})
            start=len(rows)+5
            rows.append([len(rows)+1,prefix,prefix.rsplit('.',1)[0] if '.' in prefix else None,len(prefix.split('.')),'工程',e.get('sysCode'),e.get('name'),clean(e.get('unit')),None,None,None,None,None,None,num(e,'bzzcfee'),num(e,'bzsbfee'),None,num(e,'bzcost'),e.get('id'),'EditorCellEntity（明细未读取）'])
            checks.append([prefix,e.get('sysCode'),e.get('name'),None,None,1,None,num(e,'bzcost'),None,None,uid,start,start])
            continue
        if c.get('id')!=uid or c.get('editorCellEntityId')!=e.get('id') or c.get('name')!=e.get('name'):
            mapping.append({'project':prefix,'database_entry':uid,'costfile_id':c.get('id'),'project_entity_id':e.get('id'),'costfile_entity_id':c.get('editorCellEntityId'),'project_name':e.get('name'),'budget_name':c.get('name')})
        if abs(c.get('cost',0)-num(e,'bzcost'))>1e-5:costfile_diffs.append([prefix,e.get('name'),c.get('cost'),num(e,'bzcost')])
        def global_code(code):return prefix+code[1:]
        start=len(rows)+5
        for r in local:
            r=list(r);r[0]=len(rows)+1;r[1]=global_code(r[1]) if r[1] else None;r[2]=global_code(r[2]) if r[2] else (prefix.rsplit('.',1)[0] if '.' in prefix else None)
            r[3]=len((r[1] or r[2]).split('.'))+(0 if r[1] else 1);r[18]=uid+':'+str(r[18]);rows.append(r)
        for s in local_spends:
            s=list(s);s[0]=len(spends)+1;s[1]=global_code(s[1]);s[7]=uid+':'+str(s[7]);spends.append(s)
        attached=len(local)-len(nodes);node_count+=len(nodes);zc_count+=attached
        checks.append([prefix,e.get('sysCode'),e.get('name'),len(nodes),attached,len(local),len(local_spends),num(e,'bzcost'),top['fields']['zzj'],top['fields']['zzj']-num(e,'bzcost'),uid,start,len(rows)+4])
    codes={r[1] for r in rows if r[1]}
    if len(codes)!=sum(bool(r[1]) for r in rows):raise ValueError('DUPLICATE_GLOBAL_HIERARCHY')
    if any(r[2] not in codes for r in rows if r[2]):raise ValueError('ORPHAN_GLOBAL_HIERARCHY')
    if any(s[1] not in codes for s in spends):raise ValueError('ORPHAN_RESOURCE_PARENT')
    fee_rows=[];fee_ids=set()
    for p in projects:
        sr=p.find('secFeeItemList')
        if sr is None:continue
        items=xml_by_id[sr.get('refid')].find('items')
        if items is None:continue
        for ref in sorted(items,key=lambda ref:key(xml_by_id[ref.get('refid')].get('bSID'))):
            fe=xml_by_id[ref.get('refid')];a=fe.attrib;fee_ids.add(a['id']);code=a.get('bSID')
            has_child=any(xml_by_id[x.get('refid')].get('bSID','').startswith(code+'.') for x in items)
            fee_rows.append([len(fee_rows)+1,p.get('orderCode'),p.get('name'),code,code.rsplit('.',1)[0] if '.' in code else None,len(code.split('.')),'费用分部' if has_child else '费用',a.get('sysCode'),a.get('name'),num(fe,'fee'),num(fe,'fl') if a.get('fl') else None,a.get('calcFormula'),num(fe,'ssFee') if a.get('ssFee') else None,num(fe,'bzVatPrice') if a.get('bzVatPrice') else None,num(fe,'ssVatPrice') if a.get('ssVatPrice') else None,a['id']])
    if len(fee_ids)!=sum(e.tag=='SecFeeEntity' for e in root):raise ValueError('UNLINKED_OTHER_FEES')
    diffs=[c for c in checks if c[9] is not None and abs(c[9])>1e-5]
    total=sum(c[7] for c in checks);project_cost=num(top_project,'bzcost');complete=not unreadable
    notes='；'.join(f'{c[0]} {c[2]} {c[9]:+.6f}元' for c in diffs) or '预算树根与项目目录金额一致（绝对容差0.00001元）。'
    read_databases=len({c[10] for c in checks if c[8] is not None})
    read_engines=sum(c[8] is not None for c in checks)
    partial=f'项目目录{len(checks)}个工程，已读取{read_engines}个工程明细；未读取工程仅保留目录汇总，空白数值表示未知。'
    summary=[['源文件',source.name],['数据保存时间',root.get('date')],['软件名称',root.get('appname')],['软件版本',root.get('version')],['工程数据库数量',len(expected)],['成功读取工程数据库数量',len(expected)-len(unreadable)],['未读取工程数',len(unreadable)],['项目及分组节点数',sum(e.tag=='ProjInfoEntity' for e in projects)],['已读取工程树节点数',node_count],['已读取附属主材设备记录数',zc_count],['树结构数据行数',len(rows)],['已读取人材机记录数',len(spends)],['项目其他费用记录数',len(fee_rows)],['项目目录工程造价',project_cost],['各工程目录造价合计',total],['目录造价核对差额',total-project_cost],['项目其他费用汇总（源值）',num(top_project,'bzqtf')],['预算树根与目录金额差异',notes],['预算文件与目录金额差异',json.dumps(costfile_diffs,ensure_ascii=False) if costfile_diffs else '一致（绝对容差0.00001元）。'],['预算库名称及内部标识差异',len(mapping)],['层级编号','项目使用原orderCode；工程内部原BSID的根1替换为工程orderCode，按数字分段排序。'],['定额附件','主材和设备没有原生层级号，通过父层级编号关联所属定额。'],['对象ID','数据库对象ID增加所属数据库文件标识前缀；目录及费用使用原UUID。'],['金额与计算式','保留源文件存储值及计算式文本；未重新计算预算。汇总与明细不能重复相加。'],['读取范围','项目目录、预算树、附属主材设备、人材机耗量及项目其他费用；不包含权限、审计历史、计价库及计算规则全文。']]
    summary[5][1]=read_databases
    summary[6]=['未读取工程数',len(unreadable)]
    summary.insert(7,['项目目录工程节点数',len(checks)])
    summary.insert(8,['成功读取工程明细数',read_engines])
    for u in unreadable:summary.append(['未读取工程',f"{u['project']} {u['name']}：{u['reason']}；保留项目目录汇总，明细、预算树根、差额和未知数量留空。"])
    return {'title':top_project.get('name')+'树结构','outputName':output_name+('_完整树结构.xlsx' if complete else '_树结构_含读取异常.xlsx'),'isComplete':complete,'partialSubtitle':partial,'headers':HEADERS,'rows':rows,'spendHeaders':['序号','父层级编号','费用编码','名称','单位','耗量','定额耗量','数据库对象ID'],'spends':spends,'feeHeaders':['序号','所属项目层级编号','所属项目','原费用层级编号','原父费用层级编号','原层级','标识','费用编号','名称','编制费用','费率','计算式','送审费用','编制增值税','送审增值税','源对象ID'],'fees':fee_rows,'checkHeaders':['项目层级编号','工程编号','工程名称','工程树节点数','附属主材设备数','树结构行数','人材机记录数','项目目录造价','预算树根造价','差额','数据库标识','树结构起始行','树结构结束行'],'checks':checks,'summary':summary,'mapping':mapping,'unreadable':unreadable,'costfileDifferences':costfile_diffs,'expectedDatabases':len(expected),'readDatabases':read_databases,'expectedEngines':len(checks),'readEngines':read_engines}
