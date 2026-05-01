# Azure pohovor – dalších 10 otázek a vzorové odpovědi

Tento dokument navazuje na první sadu otázek a pokrývá témata jako AKS pokročilé scénáře, cost management, disaster recovery, Azure Bastion, databáze, GitHub Actions CI/CD pipelines, tagging a governance.

---

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
