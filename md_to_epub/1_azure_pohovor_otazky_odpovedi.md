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

## 11. AKS – škálování aplikace

### Otázka
Aplikace v AKS má špičky v provozu ráno a v pátek odpoledne. Jak zajistíš automatické škálování, aby zbytečně neběžely prázdné nody v noci?

### Vzorová odpověď
V AKS se kombinují dvě vrstvy škálování. Horizontal Pod Autoscaler (HPA) škáluje počet podů podle metriky, nejčastěji CPU nebo memory utilization. Když narůstá počet podů, ale v clusteru chybí kapacita, nastupuje Cluster Autoscaler nebo modernější Karpenter, který přidá nové nody z node poolu.

V noci, kdy jsou nody nevyužité, Cluster Autoscaler jejich počet zmenší zpět na minimum dle nastavení `min-count`. Pro maximální úsporu se node pooly nastaví s minimem například na 1 nebo 2 nody, a škálují se nahoru jen při reálné potřebě.

Bonusový bod u pohovoru je zmínit, že pro plánované špičky (pátek odpoledne) lze kombinovat HPA s KEDA, které umí škálovat pody i podle vlastních metrik, například délky fronty ve Service Bus nebo Azure Queue Storage.

---

## 12. Azure Bastion vs VPN Gateway

### Otázka
Proč by zákazník použil Azure Bastion pro přístup na VM místo VPN? Kdy dáš přednost jednomu nebo druhému?

### Vzorová odpověď
Azure Bastion je spravovaná služba, která umožní RDP nebo SSH přistup na VM přímo přes Azure Portal přes HTTPS, bez nutnosti veřejné IP adresy na VM nebo VPN klienta na koncovém zařízení. Hodí se pro administrátorský přístup jednotlivých pracovníků na konkrétní VM.

VPN Gateway naproti tomu propojuje buď celou firemní síť se sítí v Azure (site-to-site), nebo umožní vzdálené uživatele připojit jako plnohodnotné členy sítě (point-to-site). To je nutné například tehdy, kdy potřebuješ přistupovat na celý rozsah privátních IP adres, Private Endpointy nebo interní DNS z jiného prostředí.

Zjednodušené pravidlo: Azure Bastion pro bezpečný přístup admina na VM bez VPN klienta, VPN Gateway pro síťové propojení, kdy potřebuješ být členem celého VNetu.

---

## 13. Cost management – jak snížit Azure účet

### Otázka
Zákazník říká, že Azure faktura výrazně narostla. Co uděláš jako první a jaké nástroje použiješ?

### Vzorová odpověď
Prvním krokem je otevřít Azure Cost Management a podívat se na breakdown nákladů podle service, resource group a subscriptions. Tam bývá hned vidět, co náklady žene nahoru – nejčastěji VM bez auto-shutdownu, zbytečně velké databázové SKU nebo opomenuté storage účty s daty.

Konkrétní opatření závisí na zjištění, ale typický postup zahrnuje: vypnutí nevyužitých VM nebo přechod na Reserved Instances pro předvídatelné workloady, snížení SKU databází, nastavení alertů při překročení budgetu a taggování resources pro přehledné přiřazení nákladů na projekty nebo týmy.

U pohovoru boduje zmínka o Azure Advisor, který automaticky generuje doporučení pro úsporu a ukazuje nevyužité nebo nadměrně alokované resources přímo v portálu.

---

## 14. Tagging a governance

### Otázka
Jak zajistíš, že každý nový resource v Azure bude mít povinné tagy jako `environment`, `owner` a `project`?

### Vzorová odpověď
Pro vynucení tagů se používá Azure Policy. Vytvoří se policy s efektem `deny` nebo `modify`, která buď zabrání vytvoření resource bez povinného tagu, nebo ho automaticky doplní z kontextu.

Pro management na více subscriptions nebo prostředích se policies spravují přes Management Groups a přiřazují se na úrovni celé hierarchie. Azure Blueprints nebo moderní ekvivalent přes Bicep/Terraform template stack zajistí, že nové subscriptions jsou od začátku nakonfigurovány správně.

Bonus: Azure Policy s efektem `modify` umí tag doplnit automaticky, například hodnotu `environment` zdědí z resource group tagu. Tím se sníží třecí plocha s vývojáři, kteří na tagy zapomínají.

---

## 15. Disaster Recovery

### Otázka
Zákazník provozuje kritickou aplikaci na Azure VM a říká, že potřebuje RTO do 1 hodiny a RPO do 15 minut. Jak to zajistíš?

### Vzorová odpověď
Pro tento scénář je vhodné Azure Site Recovery (ASR). Replikuje VM do jiného Azure regionu kontinuálně a umožní failover s RTO v řádu minut. Replikace probíhá asynchronně a RPO se konfiguruje – standardní hodnota je přibližně 30 sekund, takže 15 minutový cíl je splnitelný.

Kromě ASR je potřeba myslet i na datovou vrstvu. Pokud aplikace používá Azure SQL, databáze se nastaví jako Geo-Redundant s active geo-replication nebo failover group, aby i data byla dostupná v sekundárním regionu s minimální ztrátou.

Recovery plány v ASR umožní orchestrovat pořadí failoveru, takže se nejprve spustí databázové servery, pak aplikační tier a nakonec load balancer. Recovery plány se pravidelně testují přes test failover, který nevymaže produkci.

---

## 16. Azure Container Registry (ACR) a bezpečnost

### Otázka
Jak zabezpečíš Azure Container Registry a jak AKS cluster zajistí, že stahuje image pouze z tohoto privátního registru?

### Vzorová odpověď
ACR se zabezpečí vypnutím veřejného přístupu a přidáním Private Endpointu podobně jako u jiných PaaS služeb. Admin account se vypne a přístup se řídí výhradně přes RBAC role, například `AcrPull` pro čtení image nebo `AcrPush` pro CI/CD pipeline.

AKS cluster se napojí na ACR přes `az aks update --attach-acr`, což nastaví Managed Identity clusteru jako oprávněnou pro stahování image. Tím odpadá potřeba ručně spravovat image pull secrets v každém namespace.

Bonus: v produkci se hodí aktivovat i Azure Defender for Containers, který skenuje image v ACR na CVE zranitelnosti. Tím se zajistí, že do clusteru nevjede image s kritickými bezpečnostními problémy.

---

## 17. Azure SQL – zálohy a obnovení dat

### Otázka
Zákazník omylem smazal důležitá data z Azure SQL databáze. Co uděláš a jaké možnosti obnovy máš?

### Vzorová odpověď
Azure SQL automaticky zálohuje databáze bez nutnosti cokoliv konfigurovat. K dispozici jsou full backupy (týdně), diferenciální (každých 12 hodin) a transakční log backupy (každých 5–12 minut). Tím je pokrytý point-in-time restore na libovolný okamžik v retention period, standardně 7 dní (konfigurovatelné až 35 dní).

V portálu nebo přes CLI se provede `Restore` databáze, zvolí se čas před smazáním dat a Azure vytvoří novou databázi k danému bodu. Původní databáze zůstane nedotčena.

Pokud smazání proběhlo déle než je retention period, zbývá možnost Long-term Retention (LTR) – pokud byla předem nakonfigurována, ukládají se backupy až 10 let do Geo-Redundant Storage.

---

## 18. CI/CD pipeline do AKS

### Otázka
Popiš, jak bys navrhl GitHub Actions pipeline pro build a deploy Docker image do AKS clusteru.

### Vzorová odpověď
Pipeline se standardně skládá z několika stages. Nejprve build: checkout kódu, `docker build`, run unit testů. Pak push: přihlášení do ACR přes `azure/docker-login` action s OIDC federation (bez long-lived secrets) a push image s tagem podle commit SHA nebo verze.

Deploy stage pak přihlásí do AKS přes `azure/aks-set-context`, aplikuje manifest nebo Helm chart s novou verzí image a počká na rollout. Pokud health checky selžou, pipeline spustí `kubectl rollout undo` jako automatický rollback.

Klíčový detail pro pohovor: přihlašování do Azure z GitHub Actions by mělo jít přes Workload Identity Federation (OIDC), nikoli přes long-lived service principal secret. Tím odpadá nutnost spravovat a rotovat secrets v GitHub repozitáři.

---

## 19. VNet Peering a hub-spoke architektura

### Otázka
Co je VNet Peering a jak funguje hub-spoke architektura? Proč peering není tranzitivní?

### Vzorová odpověď
VNet Peering propojí dvě VNets na síťové úrovni s nízkou latencí přes páteřní Azure síť, bez nutnosti VPN nebo veřejné sítě. Po spárování spolu resources v obou VNets komunikují přes privátní IP adresy.

Hub-spoke architektura využívá jeden centrální Hub VNet, kde bydlí sdílené služby – Azure Firewall, VPN Gateway, Bastion, Private DNS. Spoke VNety obsahují workloady a jsou napeerované na Hub. Spoke-to-spoke komunikace prochází přes Hub, kde se může centrálně filtrovat a logovat.

Peering není tranzitivní: pokud Spoke A a Spoke B jsou napeerované na Hub, automaticky to neznamená, že Spoke A a Spoke B spolu komunikují. Provoz mezi nimi musí explicitně projít přes Hub s nakonfigurovaným Azure Firewallem nebo NVA (Network Virtual Appliance).

---

## 20. Entra ID – Conditional Access

### Otázka
Co je Conditional Access v Entra ID a jak bys použil tuto funkci k zabezpečení přístupu do Azure Portalu?

### Vzorová odpověď
Conditional Access je mechanismus Entra ID, který vyhodnocuje podmínky přihlášení a na základě nich povolí nebo zamítne přístup, případně vyžádá vícefaktorové ověření (MFA). Podmínky mohou zahrnovat lokaci uživatele, typ zařízení, rizikové skóre přihlášení nebo konkrétní cílovou aplikaci.

Pro přístup do Azure Portalu by se vytvořila policy, která vyžaduje MFA pro všechny uživatele mimo firemní síť nebo pro uživatele s privilegovanými rolemi (Owner, Contributor) vždy bez výjimky. Tím se výrazně snižuje riziko kompromitace účtu přes phishing nebo uniklé heslo.

Bonus pro pohovor: Conditional Access funguje dobře v kombinaci s Privileged Identity Management (PIM), kde uživatel nemá trvale přiřazenou vysokou roli, ale musí si ji aktivovat on-demand a teprve potom Conditional Access prověří podmínky přístupu.

---

## Jak odpovědi využít u pohovoru

Odpovědi jsou formulované tak, aby zazněly přirozeně v rozhovoru. Dobrá technika je nejprve říct klíčové komponenty, pak postup a na konci přidat praktický detail nebo typickou chybu. Tazatelé zpravidla oceňují odpovědi, které ukazují, co se stane při selhání nebo co jsi viděl v praxi, víc než odpovědi, které jen vyjmenují funkce dané služby.

## 21. Key Vault – soft delete a purge protection

### Otázka
Co je soft delete a purge protection v Azure Key Vault a proč je důležité je mít zapnuté?

### Vzorová odpověď
Soft delete zajišťuje, že smazaný objekt (secret, klíč, certifikát) nebo celý Key Vault není odstraněn okamžitě, ale přesune se do stavu smazáno a zůstane dostupný pro obnovu po dobu retence (výchozí 90 dní). Bez soft delete by neúmyslné smazání znamenalo nevratnou ztrátu dat.

Purge protection přidává další vrstvu: pokud je zapnuta, ani administrátor ani automatizace nemůže trvale smazat objekt během retence. Tím se brání útokům nebo chybám, které by jinak šly provést i přes soft delete obejitím.

U pohovoru je dobré doplnit, že od roku 2023 je soft delete pro nové Key Vaults v Azure zapnutý automaticky a nejde ho vypnout. Purge protection je nicméně stále volitelná a v produkčních prostředích s citlivými daty nebo certifikáty by měla být vždy zapnuta.

---

## 22. Key Vault – rozdíl mezi Keys, Secrets a Certificates

### Otázka
Jaký je v Key Vault rozdíl mezi Keys, Secrets a Certificates? Kdy použiješ co?

### Vzorová odpověď
Keys jsou kryptografické klíče pro šifrování, dešifrování nebo podepisování. Klíč může zůstat celý v Key Vault HSM a aplikace ho nikdy nestáhne jako soubor – místo toho volá Key Vault API, které operaci provede interně. Tím se klíčový materiál nikdy nedostane do aplikace.

Secrets jsou libovolné textové hodnoty – hesla, connection stringy, API klíče nebo tokeny. Aplikace si secret stáhne a použije ho lokálně. Secrets nemají kryptografické vlastnosti, jen bezpečné uložení a řízení přístupu.

Certificates jsou X.509 certifikáty, které Key Vault ukládá jako celek včetně privátního klíče. Key Vault zároveň umí spravovat jejich lifecycle – automaticky obnovovat certifikát u integrovaných CA jako DigiCert nebo Let's Encrypt a notifikovat při blížící se expiraci.

---

## 23. Terraform – remote state a state locking

### Otázka
Proč musíš mít Terraform state uložený vzdáleně a co je state locking? Co se stane, když se state lock nepodaří?

### Vzorová odpověď
Lokální state soubor funguje jen pro jednoho uživatele na jednom stroji. V týmu nebo v CI/CD pipeline by souběžné spuštění dvou `terraform apply` vedlo ke konfliktu – oba by četly stejný stav, každý by provedl změny a výsledek by byl nekonsistentní nebo poškozený state soubor.

Remote backend v Azure Storage řeší obojí: state je centrálně uložen v blob storage a state locking (přes Azure Blob lease nebo Terraform Cloud lock) zajistí, že v danou chvíli může apply provádět jen jeden proces. Ostatní čekají nebo dostanou chybu.

Pokud lock zůstane viset například po selhání pipeline, je potřeba ho manuálně uvolnit přes `terraform force-unlock`. Toho je potřeba být opatrný – uvolnit lock se smí jen tehdy, když je jisté, že žádný jiný apply neběží, jinak hrozí právě ten souběžný konflikt, kterému se lock snaží předejít.

---

## 24. Terraform drift detection

### Otázka
Vývojář ručně změnil konfiguraci VM přes Azure Portal. Jak zjistíš, že Terraform drift nastal, a jak ho vyřešíš?

### Vzorová odpověď
Drift je stav, kdy reálná infrastruktura neodpovídá Terraform state souboru nebo kódu. Zjistí se spuštěním `terraform plan` bez apply – pokud plán zobrazí změny přesto, že kód nebyl upraven, nastal drift.

Pro automatizované sledování lze naplánovat pipeline, která pravidelně spouští `terraform plan` v read-only módu a odesílá výstup na alert nebo do ticketovacího systému. Pokud je výstup nenulový, tým ví, že někdo provedl manuální změnu mimo IaC.

Řešení mají dvě varianty: buď `terraform apply` přepíše manuální změnu zpět na stav definovaný kódem (preferovaný přístup v silném IaC modelu), nebo se kód aktualizuje tak, aby manuální změnu zachytil a stal se opět zdrojem pravdy. Manuální změny portálem by se obecně měly v produkci blokovat přes RBAC.

---

## 25. Azure DNS – privátní a veřejné zóny

### Otázka
Jaký je rozdíl mezi Azure Public DNS Zone a Azure Private DNS Zone? Kdy potřebuješ obojí?

### Vzorová odpověď
Public DNS Zone hostuje záznamy, které jsou viditelné z internetu – A, CNAME, MX a další záznamy pro veřejnou doménu. Azure tuto zónu slouží jako autoritativní DNS server dostupný z celého internetu.

Private DNS Zone je viditelná jen pro resources uvnitř VNetu nebo VNetů, které jsou s ní explicitně propojeny přes VNet link. Využívá se hlavně pro privátní name resolution u Private Endpointů, například `myserver.privatelink.database.windows.net` překládá na privátní IP místo veřejné.

V praxi jsou obě potřebné souběžně. Veřejná zóna obsluhuje uživatele z internetu, privátní zóna zajišťuje, že resources uvnitř VNetu komunikují přes privátní IP adresy bez zbytečného přechodu přes veřejnou síť.

---

## 26. Azure Load Balancer vs Application Gateway vs Front Door

### Otázka
Vysvětli rozdíl mezi Azure Load Balancer, Application Gateway a Azure Front Door. Kdy použiješ co?

### Vzorová odpověď
Azure Load Balancer pracuje na L4 – TCP/UDP – a distribuuje provoz mezi backend VM nebo instance v rámci jednoho regionu. Nemá přehled o HTTP obsahu, neřeší SSL terminaci ani routování podle URL. Hodí se pro non-HTTP workloady nebo jako interní balancer mezi tiers.

Application Gateway je L7 balancer v rámci jednoho regionu. Rozumí HTTP/HTTPS, umí routovat podle URL path nebo hostname, provádí SSL terminaci a má integrovaný WAF (Web Application Firewall). Je správnou volbou pro HTTP aplikace v jednom regionu.

Azure Front Door je globální L7 entry point s anycast sítí. Zajišťuje SSL terminaci na nejbližším PoP (Point of Presence), cachování, WAF a globální routování s health-based failoverem mezi regiony. Použije se tehdy, kdy aplikace obsluhuje uživatele z celého světa a potřebuje minimalizovat latenci nebo globální redundanci.

---

## 27. Workload Identity pro AKS

### Otázka
Co je Workload Identity pro AKS a proč je to lepší než starší AAD Pod Identity?

### Vzorová odpověď
Workload Identity je moderní způsob, jak přiřadit Managed Identity konkrétnímu Kubernetes service accountu. Pod pak může získat Azure token bez jakéhokoliv uloženého secretu – místo toho se používá OIDC federation mezi Entra ID a AKS OIDC issuerem.

Starší AAD Pod Identity fungovala přes DaemonSet a MIC/NMI komponenty, které interceptovaly IMDS volání. To přinášelo latenci, komplexitu a bezpečnostní riziko – jakýkoli pod s dostatečnými oprávněními mohl potenciálně získat token jiného podu.

Workload Identity jde přes standardní Kubernetes service account token, který projde OIDC exchange u Entra ID. Je to průmyslový standard, jednodušší na správu, bez extra komponent v clusteru a bez potřeby spravovat jakékoliv secrety v manifestech.

---

## 28. Azure Monitor – Log Analytics KQL

### Otázka
Napiš KQL dotaz, který ukáže průměrné CPU využití všech VM za posledních 24 hodin, seřazené sestupně.

### Vzorová odpověď
U pohovoru nemusíš mít dotaz přesně nazpaměť, ale měl bys ukázat, že rozumíš struktuře tabulek a základním operátorům:

```kql
Perf
| where TimeGenerated > ago(24h)
| where CounterName == "% Processor Time"
| where ObjectName == "Processor"
| where InstanceName == "_Total"
| summarize AvgCPU = avg(CounterValue) by Computer
| order by AvgCPU desc
```

Tabulka `Perf` ukládá výkonnostní čítače z VM s nainstalovaným Azure Monitor Agentem. Klíčové operátory jsou `where` pro filtrování, `summarize` pro agregaci a `order by` pro řazení. Pro reálný dashboard by se výsledek doplnil o `render timechart` pro vizualizaci.

---

## 29. Azure Security Center / Microsoft Defender for Cloud

### Otázka
Co je Microsoft Defender for Cloud a jaký je rozdíl mezi free a placenými plány?

### Vzorová odpověď
Microsoft Defender for Cloud je centrální bezpečnostní nástroj, který kontinuálně hodnotí bezpečnostní posture Azure prostředí, detekuje hrozby a dává doporučení. Dříve se jmenoval Azure Security Center a Azure Defender – nyní jsou sloučeny pod jeden brand.

Free tier přináší Secure Score, základní doporučení podle benchmarků (CIS, Azure Security Benchmark) a přehled compliance. Je dostupný bez poplatků pro všechny subscriptions.

Placené Defender plány (Defender for Servers, Defender for Containers, Defender for SQL atd.) přidávají aktivní threat detection, just-in-time VM access, adaptive application controls, vulnerability assessment a integraci s Microsoft Sentinel pro SIEM/SOAR. Každý plán se platí za resource, takže je možné zapnout ochranu jen pro kritické workloady.

---

## 30. Azure Lighthouse a multi-tenant správa

### Otázka
Co je Azure Lighthouse a k čemu ho použiješ jako MSP nebo cloud konzultant?

### Vzorová odpověď
Azure Lighthouse umožní poskytovateli spravovaných služeb (MSP) nebo konzultantovi spravovat Azure prostředí zákazníka ze svého vlastního tenanta bez nutnosti vytvářet guest účty nebo sdílet přihlašovací údaje. Zákazník deleguje přístup k subscription nebo resource group přes ARM deployment a MSP vidí tato prostředí ve svém portálu vedle svých vlastních.

Z pohledu auditability je to čistší než alternativy – každá akce MSP je viditelná v Azure Activity Log zákazníka pod jasně identifikovatelnou identitou. Zákazník má přehled, co kdy kdo dělal, a přístup může kdykoliv odvolat.

Pro firmu na pozici cloud administrátora nebo MSP partnera je znalost Lighthouse signálem, že kandidát rozumí enterprise a multi-tenant scénářům, nejen jednomu prostředí. V praxi se používá v kombinaci s Azure Policy a Azure Monitor pro centrální governance a monitoring více zákazníků z jednoho místa.

---

## Jak odpovědi využít u pohovoru

Odpovědi v této sadě pokrývají témata, která jsou méně obvyklá, ale výrazně odliší kandidáta od průměru. Klíčové oblasti jsou správa certifikátů v Key Vault, Terraform v CI/CD, DNS architektura a globální routing. Pohovorující typicky testují hloubku znalostí dotazem "a co se stane když to selže?" nebo "proč je tohle lepší než alternativa?" – proto každá odpověď obsahuje i srovnávací kontext.
