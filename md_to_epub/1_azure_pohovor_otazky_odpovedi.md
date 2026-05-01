# Azure pohovor – otázky a vzorové odpovědi

Tento dokument shrnuje modelové otázky a odpovědi pro technický pohovor na roli zaměřenou na správu a návrh prostředí v Microsoft Azure. Odpovědi jsou formulované tak, aby zněly přirozeně u pohovoru a zároveň pokrývaly praktické detaily, které často vedou na doplňující otázky.

## 1. NSG vs Azure Firewall

### Otázka
Jaký je rozdíl mezi NSG a Azure Firewall? Kdy použít jedno a kdy druhé?

### Vzorová odpověď
NSG je Network Security Group, tedy sada pravidel pro povolení nebo blokování provozu na úrovni subnetu nebo síťové karty. Pracuje hlavně na L3/L4, tedy podle IP adres, portů a protokolů.[cite:2][cite:9]

Azure Firewall je centralizovaný, spravovaný firewall, který pokrývá nejen L3/L4, ale i vyšší vrstvy, včetně pravidel podle FQDN nebo aplikačních scénářů. Nasazuje se do dedikovaného subnetu a hodí se pro centrální řízení provozu mezi sítěmi a směrem do internetu.[cite:1][cite:2]

V praxi se často používají obě služby dohromady. NSG slouží pro segmentaci a základní ochranu workloadů, zatímco Azure Firewall řeší centrální bezpečnostní politiku, odchozí provoz a pokročilejší filtrování.[cite:1][cite:9]

## 2. AKS aplikace na internetu se SSL

### Otázka
Máš AKS cluster. Potřebuješ vystavit aplikaci na internet s vlastním SSL certifikátem. Jak to uděláš a jaké Azure komponenty použiješ?

### Vzorová odpověď
Použil by se ingress pro HTTP/HTTPS routing do clusteru a před něj buď Azure Application Gateway, nebo ingress controller typu NGINX podle architektury řešení. Pokud je cílem enterprise scénář s centralizovaným TLS a případně WAF, dává největší smysl Application Gateway.[cite:60]

Certifikát je vhodné uložit do Azure Key Vault a nepřenášet ho jako soubor v repozitáři nebo přímo v manifestu. V produkci je dobré kombinovat bezpečné uložení certifikátu, automatickou obnovu a jasně oddělit TLS terminaci od samotných podů.[cite:60]

U pohovoru je dobré říct i to, že DNS musí mířit na veřejnou IP ingress vrstvy a že podle konkrétního návrhu může TLS končit na Application Gateway nebo až v ingress controlleru. Tím se ukáže, že odpověď není jen teoretická, ale počítá i s provozní realitou.

## 3. Monitoring a alerting v Azure

### Otázka
Jak nastavit monitoring a alerting pro Azure infrastrukturu, dashboard a email při CPU nad 90 %?

### Vzorová odpověď
Základem je Azure Monitor pro metriky a alerty a Log Analytics Workspace pro centralizaci logů. App Service, VM a další služby mohou posílat diagnostická data přes Diagnostic Settings, zatímco nad logy a metrikami se potom staví alerty, dashboardy a Workbooks.[cite:41][cite:46]

Pro VM alert by se vytvořilo pravidlo nad metrikou Percentage CPU, například nad 90 % po určitou dobu, a k němu Action Group s emailem nebo webhookem. Pokud má zákazník chtít přehledový dashboard, hodí se Azure Dashboard nebo Azure Workbooks; pro týmy zvyklé na observability stack lze přidat i Grafanu.[cite:46]

U pohovoru boduje zmínka o tom, že logy je lepší centralizovat do Log Analytics než spoléhat jen na jednotlivé resource obrazovky. To usnadňuje troubleshooting, audit i sdílení přístupů.[cite:41][cite:43]

## 4. Automatické vypínání a zapínání VM

### Otázka
Zákazník chce každý večer vypínat všechny testovací VM v resource group `rg-test` a ráno je zase zapínat. Jak to vyřešit?

### Vzorová odpověď
Nejlepší odpověď je Azure Automation Account s runbookem a plánem spuštění. Terraform je zde vhodný pro deployment celé automatizace, ale samotné časované vypnutí a zapnutí neprovádí Terraform přímo, nýbrž Azure Automation nebo jiný scheduler.[cite:14][cite:18]

Typický návrh je vytvořit Automation Account, PowerShell runbook pro start a stop, dva scheduly a jejich navázání na runbooky. Pro čisté nightly vypnutí lze v některých případech použít i vestavěný auto-shutdown mechanismus, ale pro obousměrné stop/start řízení bývá runbook flexibilnější.[cite:14][cite:18]

U pohovoru je ideální formulace: Terraformem nasadím Automation Account, runbooky a scheduly, ale runtime operaci bude řešit Azure Automation. Tím se ukáže správné rozlišení mezi IaC a provozní automatizací.[cite:14]

## 5. HTTPS certifikát pro App Service

### Otázka
Zákazník má webovou aplikaci na Azure App Service a potřebuje HTTPS s vlastním doménovým certifikátem. Jak certifikát bezpečně uložit a napojit?

### Vzorová odpověď
Bezpečný návrh je uložit certifikát do Azure Key Vault a App Service napojit tak, aby se certifikát neřešil ručně jako soubor po prostředí. Vhodné je kombinovat vlastní doménu, TLS/SSL binding a bezpečný přístup k tajným údajům přes identitu místo statických hesel.

V produkční odpovědi je dobré zmínit i obnovu certifikátu, audit přístupů a to, že tajné údaje nemají být v repozitáři ani v pipeline jako prostý soubor. Taková odpověď dobře sedí na roli administrátora i cloud engineera.

## 6. AKS pody se nepřipojí k Azure SQL

### Otázka
Máš AKS cluster a pody se nedokáží připojit k Azure SQL databázi. Jak problém budeš debugovat?

### Vzorová odpověď
Postup je odspodu nahoru. Nejprve se ověří, že databáze opravdu běží, potom se zkontrolují logy aplikace a stav podu a nakonec se testuje konektivita přímo z podu, například přes `nslookup`, `nc` nebo `telnet` na port 1433.[cite:25][cite:27]

Pak je potřeba projít síťovou cestu. Kontrolují se firewall pravidla na SQL serveru, případně VNet pravidla, NSG na subnetech a hlavně DNS, pokud je použitý Private Endpoint.[cite:27][cite:32]

Častá příčina je špatné DNS rozlišení u Private Endpointu. Když CoreDNS nebo přidružená Private DNS zóna vrátí veřejnou IP místo privátní, aplikace se snaží připojit špatnou cestou a spojení selže.[cite:32]

## 7. Vývojáři mají číst logy, ale nesmí nic měnit

### Otázka
Jak nastavit v Azure, aby vývojáři četli logy z App Service, ale nesměli měnit konfiguraci?

### Vzorová odpověď
Nejčistší řešení je posílat logy z App Service do Log Analytics Workspace a vývojářům dát jen čtecí přístup k tomuto workspace. Tím získají přístup k logům přes Azure Monitor a KQL, ale nedostanou oprávnění měnit samotnou App Service konfiguraci.[cite:41][cite:43]

Pouhá role Reader na App Service je sice read-only, ale má háček: nestačí pro live Log Stream. Pro live Log Stream bývá potřeba vyšší oprávnění, což je důvod, proč je centralizace logů do Log Analytics bezpečnější a lépe spravovatelná.[cite:40]

U pohovoru se hodí doplnit princip least privilege a ideálně i to, že role se přiřazují skupinám v Entra ID, ne jednotlivcům. Tím odpověď působí provozně vyzráleji.

## 8. Private Endpoint vs Service Endpoint

### Otázka
Co je Private Endpoint a jak se liší od Service Endpoint?

### Vzorová odpověď
Service Endpoint rozšiřuje identitu VNetu ke konkrétní PaaS službě, ale služba sama stále zůstává dostupná přes svůj veřejný endpoint. Je to jednoduché a levné řešení, ale z pohledu izolace není tak silné jako Private Link.[cite:51][cite:63]

Private Endpoint vytvoří privátní síťové rozhraní s privátní IP adresou ve VNetu, takže se ke službě přistupuje přes interní adresaci. Veřejný přístup na službu se potom dá úplně vypnout, což je běžný požadavek u SQL, Key Vaultu nebo App Service v citlivějších prostředích.[cite:54][cite:60][cite:63]

Důležitá je i DNS vrstva. Private Endpoint téměř vždy vyžaduje správně nastavenou Private DNS zónu, jinak jméno služby může stále překládat na veřejnou IP a návrh ztrácí smysl.[cite:51][cite:63]

## 9. Service Principal vs Managed Identity

### Otázka
Vysvětli rozdíl mezi Service Principal a Managed Identity. Kdy použít jedno a kdy druhé?

### Vzorová odpověď
Service Principal je identita pro aplikaci nebo automatizaci, u které se obvykle spravuje client secret nebo certifikát. To znamená, že je potřeba řešit bezpečné uložení, rotaci a expiraci přihlašovacích údajů.

Managed Identity je vhodná hlavně pro Azure resource, protože Azure spravuje životní cyklus identity i získávání tokenů. U pohovoru se vyplatí říct jednoduché pravidlo: pokud workload běží přímo v Azure, preferuje se Managed Identity; pokud jde o externí systém nebo CI/CD mimo Azure, často dává smysl Service Principal.

## 10. Návrh plně privátního dev prostředí

### Otázka
Zákazník chce nové prostředí pro dev tým: VNet, 2 VM, App Service, Azure SQL a Key Vault. Vše musí být privátní a bez veřejného přístupu. Jak to navrhnout?

### Vzorová odpověď
Základ je rozdělit prostředí do více subnetů, například pro VM, aplikační integraci, Private Endpointy a GatewaySubnet pro VPN. Samotná VPN řeší přístup uživatelů do prostředí, ale sama o sobě nestačí k tomu, aby byly PaaS služby neveřejné.[cite:49][cite:50]

App Service, Azure SQL a Key Vault by měly mít Private Endpointy a veřejný přístup vypnutý. Pro správnou funkci je potřeba přidat Private DNS zóny, jinak jména služeb nemusí ukazovat na privátní IP adresy.[cite:54][cite:60][cite:63]

VM by neměly mít veřejné IP adresy a přístup na ně by měl být povolen jen přes VPN nebo jinou privátní cestu. Celý návrh je vhodné nasadit přes Terraform, aby byl opakovatelný, auditovatelný a snadno rozšiřitelný.

## Jak to říkat u pohovoru

Dobrá odpověď nebývá jen definice služby, ale krátký návrh postupu. Silná struktura odpovědi je: co bych použil, proč právě to, jaké jsou hlavní komponenty a na co si dát pozor v provozu.

Velmi často zaboduje i zmínka o typických chybách, například špatné DNS u Private Endpointů, záměna NSG s ASG, nebo představa, že Terraform sám o sobě řeší časované runtime operace. Taková odpověď ukazuje praktickou zkušenost, ne jen naučené pojmy.[cite:9][cite:14][cite:32][cite:63]
