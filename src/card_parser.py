import re

def clean_noise(text: str) -> str:
    """清理常見的邊緣雜訊字元與標點符號"""
    text = re.sub(r'[國業毎劵潮進館體是廣|I•〇]+$', '', text)
    return text.strip(' ,;，、')

def parse_card_fields(lines: list) -> dict:
    """
    從名片文字清單中智慧分析抽取結構化欄位：
    姓名、職稱、公司名稱、行動電話、公司電話、傳真、Email、地址、統一編號、官方網站
    """
    cleaned = [clean_noise(l) for l in lines if l.strip()]
    full_text = "\n".join(cleaned)
    
    info = {
        "公司名稱": "",
        "姓名": "",
        "職稱": "",
        "行動電話": "",
        "公司電話": "",
        "傳真": "",
        "Email": "",
        "地址": "",
        "統一編號": "",
        "網站": "",
        "原始文字": " | ".join(cleaned)
    }
    
    # 1. Email (支援常見 OCR 域名除錯)
    emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', full_text)
    if emails:
        raw_email = emails[0]
        raw_email = re.sub(r'gmair\.(com|comm)', 'gmail.com', raw_email, flags=re.I)
        raw_email = re.sub(r'\.co\.ik$', '.co.uk', raw_email, flags=re.I)
        raw_email = re.sub(r'ms65\.Hinet\.net', 'ms65.hinet.net', raw_email, flags=re.I)
        raw_email = re.sub(r'swinerocoms57\.hinet', 'swinero@ms57.hinet', raw_email, flags=re.I)
        info["Email"] = raw_email.lower()
    
    # 2. 官方網站
    webs = re.findall(r'(?:https?://|www\.)[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+|[a-zA-Z0-9-]+\.(?:com|org|tw|net)(?:\.tw)?', full_text, re.IGNORECASE)
    for w in webs:
        if "@" not in w and not w.endswith('.jpg') and not w.endswith('.png'):
            if not info["Email"] or w.lower() != info["Email"].split('@')[-1].lower():
                info["網站"] = w.lower()
                break

    # 3. 統一編號 (台灣 8 碼商業登記號碼)
    tax = re.search(r'(?:統編|統一編號|統\s*編)[:：\s]*(\d{8})', full_text)
    if not tax:
        for cand in re.findall(r'\b(\d{8})\b', full_text):
            if not cand.startswith(('09', '02', '03', '04', '05', '06', '07', '08')):
                info["統一編號"] = cand
                break
    else:
        info["統一編號"] = tax.group(1)

    # 4. 行動電話 (Mobile)
    mobiles = []
    tw_mob = re.findall(r'(?:09\d{2}[-\s]?\d{3}[-\s]?\d{3}|\+?886[-\s]?9\d{2}[-\s]?\d{3}[-\s]?\d{3})', full_text)
    mobiles.extend(tw_mob)
    intl_mob = re.findall(r'\+234[-\s]?\d{9,11}', full_text)
    mobiles.extend(intl_mob)
    if mobiles:
        clean_mob = re.sub(r'[^\d+]', '', mobiles[0])
        if clean_mob.startswith('09') and len(clean_mob) == 10:
            info["行動電話"] = f"{clean_mob[:4]}-{clean_mob[4:7]}-{clean_mob[7:]}"
        elif clean_mob.startswith('8869') and len(clean_mob) == 12:
            info["行動電話"] = f"+886-{clean_mob[3:6]}-{clean_mob[6:9]}-{clean_mob[9:]}"
        else:
            info["行動電話"] = clean_mob

    # 5. 公司市話 / 傳真
    for line in cleaned:
        if re.search(r'FAX|傳真', line, re.I):
            m = re.search(r'0\d{1,2}[-\s]?\d{6,8}', line)
            if m: info["傳真"] = m.group(0)
        elif re.search(r'TEL|電話|Phone', line, re.I):
            m = re.search(r'(?:0\d{1,2}[-\s]?\d{6,8}|\+?\d{2,3}[-\s]?\d{1,2}[-\s]?\d{6,8})', line)
            if m and not info["公司電話"]:
                info["公司電話"] = m.group(0)
        elif not info["公司電話"] and re.search(r'\b0\d{1,2}[-\s]\d{6,8}\b', line):
            info["公司電話"] = re.search(r'\b0\d{1,2}[-\s]\d{6,8}\b', line).group(0)

    # 6. 地址 (支援台灣各縣市以及常見英文國際地址)
    addr_match = re.search(r'(?:\d{3,5})?\s*(?:台[北市南中]|新[北市竹]|桃園市|高雄市|基隆市|嘉義市|苗栗縣|彰化縣|南投縣|雲林縣|嘉義縣|屏東縣|宜蘭縣|花蓮縣|台東縣)[^\n,，。]{4,45}', full_text)
    if addr_match:
        info["地址"] = addr_match.group(0).strip()
    else:
        en_addr = re.search(r'(?:No\.\s*\d+.*(?:Rd|St|Lane|Ln|Sec|Dist|City|Taiwan)|Block\s*\d+.*|Area\s*\d+.*)', full_text, re.I)
        if en_addr:
            info["地址"] = en_addr.group(0).strip()

    # 7. 職稱 (Title)
    titles = [
        "董事長", "總經理", "副總經理", "副處長", "處長", "秘書長", "執行長", "特助", 
        "協理", "經理", "副理", "主任", "工程師", "行銷業務經理", "業務主管", "專員", "顧問", 
        "Special Assistant", "Director", "Manager", "Ambassador", "Amb."
    ]
    for line in cleaned:
        for t in titles:
            if t in line:
                info["職稱"] = t
                cand = line.replace(t, '').strip(' :：')
                if 2 <= len(cand) <= 6 and not any(k in cand for k in ["公司", "協會", "企業"]):
                    info["姓名"] = cand
                break
        if info["職稱"]: break

    # 8. 公司名稱 (Company Name)
    company_kw = ["有限公司", "股份有限公司", "協會", "辦事處", "事務所", "科技", "企業", "Co., Ltd", "Co.,Ltd", "LLC", "Ministry", "Department", "Trade Office"]
    for line in cleaned:
        for kw in company_kw:
            if kw in line and len(line) < 40 and not any(k in line for k in ["地址", "會址", "網址", "TEL", "FAX", "Email", "統編"]):
                info["公司名稱"] = line
                break
        if info["公司名稱"]: break

    # 9. 姓名 (Name)
    if not info["姓名"]:
        for line in cleaned:
            if re.match(r'^[\u4e00-\u9fa5]{2,3}$', line):
                if line != info["職稱"] and line not in info["公司名稱"] and line not in ["電話", "傳真", "網址", "統編", "會址"]:
                    info["姓名"] = line
                    break
            elif re.match(r'^(?:Mr\.|Amb\.|Dr\.)?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)', line):
                info["姓名"] = line
                break

    return info
