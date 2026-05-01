# Azure pohovor – čtvrtá sada: Trade-offs a více možností řešení

Tato sada otázek je zaměřena na architektonická rozhodnutí. Každá otázka má více variant řešení a tabulku trade-offs, abyste mohli u pohovoru ukázat, že nejen znáte možnosti, ale rozumíte i tomu, proč v daném kontextu vybrat jednu nad druhou.

---

## 31. Jak spustit kontejnerovou aplikaci v Azure?

### Otázka
Zákazník chce nasadit jednoduchý REST API backend jako kontejner. Jaké možnosti má a kdy bys zvolil která?

### Možnosti řešení

**Varianta A – Azure Container Instances (ACI)**
Serverless kontejner bez správy infrastruktury. Spustí se za sekundy, platí se jen za čas běhu. Vhodné pro dávkové úlohy, jednorázové tasky nebo dev/test. Nemá built-in load balancing ani auto-scaling.

**Varianta B – Azure Container Apps (ACA)**
Spravovaná platforma nad Kubernetes (KEDA + Dapr). Podporuje auto-scaling na nulu, HTTP ingress, HTTPS, revize a traffic splitting. Ideální pro event-driven nebo HTTP microservices bez nutnosti spravovat Kubernetes.

**Varianta C – Azure Kubernetes Service (AKS)**
Plná kontrola nad clusterem. Vhodné pro komplexní multi-service systémy, vlastní networking, pokročilé scheduling požadavky. Vyžaduje správu node poolů, upgradů a bezpečnostních oprav.

**Varianta D – Azure App Service (Web App for Containers)**
Spravovaná PaaS pro kontejnery s built-in deployment slots, auto-scaling a snadnou integrací s CI/CD. Vhodné pro jednoduché webové aplikace nebo API bez potřeby Kubernetes.

### Trade-off tabulka

| Kritérium | ACI | Container Apps | AKS | App Service |
|---|---|---|---|---|
| Správa infrastruktury | ✅ Žádná | ✅ Žádná | ❌ Vyžaduje | ✅ Žádná |
| Auto-scaling na nulu | ❌ | ✅ | ✅ s KEDA | ❌ |
| Komplexní multi-service | ❌ | ✅ | ✅ | ❌ |
| Cena (idle) | Nízká | Nízká | Střední–Vysoká | Střední |
| Deployment slots | ❌ | ✅ revize | ❌ nativně | ✅ |
| Plná K8s kontrola | ❌ | ❌ | ✅ | ❌ |

### Doporučení
- **Jednoduchý API, malý tým**: Container Apps
- **Komplexní systém, zkušený DevOps tým**: AKS
- **Rychlý POC nebo batch job**: ACI
- **Tradiční web aplikace**: App Service

---

## 32. Jak uložit stav aplikace – volba databáze v Azure

### Otázka
Aplikace potřebuje persistentní úložiště. Zákazník neví, jestli chce relační nebo NoSQL databázi. Jak jim pomůžeš rozhodnout?

### Možnosti řešení

**Varianta A – Azure SQL Database**
Plně spravovaný Microsoft SQL Server. ACID transakce, silná konzistence, bohatý SQL dialekt, integrované zálohy a geo-replikace.

**Varianta B – Azure Database for PostgreSQL (Flexible Server)**
Open-source relační DB, oblíbená v cloud-native světě. Silná podpora JSON, extensions (PostGIS, pgvector pro AI scénáře), levnější licence.

**Varianta C – Azure Cosmos DB**
Globálně distribuovaná NoSQL databáze s více API (SQL, MongoDB, Cassandra, Gremlin). Garantuje SLA na latenci, throughput a availability. Multi-region write je unikátní vlastnost.

**Varianta D – Azure Cache for Redis**
In-memory úložiště pro session state, cache nebo pub/sub. Není primární databáze, ale zásadní pro výkon aplikací s opakovanými read dotazy.

### Trade-off tabulka

| Kritérium | Azure SQL | PostgreSQL | Cosmos DB | Redis |
|---|---|---|---|---|
| Transakce (ACID) | ✅ Silné | ✅ Silné | ✅ Limitované | ❌ |
| Škálování čtení | Střední | Střední | ✅ Globální | ✅ Velmi rychlé |
| Schema-less / flexibilní | ❌ | Částečně | ✅ | ❌ |
| Cena při malém provozu | Nízká | Nízká | Střední–Vysoká | Nízká |
| Latence | ms | ms | < 10 ms SLA | < 1 ms |
| Vhodné pro AI / vektory | ❌ | ✅ pgvector | ✅ | ❌ |

### Doporučení
- **ERP, finance, silná konzistence**: Azure SQL
- **Open-source, cloud-native, AI workloady**: PostgreSQL Flexible Server
- **Globální distribuce, IoT, high-throughput**: Cosmos DB
- **Session cache, rychlé čtení**: Redis jako doplněk

---

## 33. Jak zajistit přístup vývojářů na Azure bez trvalých oprávnění?

### Otázka
Vývojáři potřebují občas přístup k produkční subscription kvůli troubleshootingu. Jak to nastavit bezpečně?

### Možnosti řešení

**Varianta A – Trvalá RBAC role Contributor**
Nejjednodušší, ale nejrizikovější. Vývojář má přístup neustále, i když ho nepotřebuje. Velká plocha pro útok nebo neúmyslnou změnu.

**Varianta B – Privileged Identity Management (PIM)**
Vývojář má eligible roli, kterou si aktivuje on-demand na omezenou dobu (např. 2 hodiny) s odůvodněním a volitelným schválením manažera. Po uplynutí doby přístup automaticky expiruje.

**Varianta C – Just-in-Time VM Access (JIT)**
Microsoft Defender for Cloud funkce pro VM. Otevře RDP/SSH port jen na konkrétní IP a časový interval po explicitní žádosti. Chrání VM před brute-force útoky.

**Varianta D – Custom RBAC + Azure Bastion**
Vlastní role pouze s read oprávněními + Bastion pro přístup na VM. Bez PIM, ale s omezeným scope.

### Trade-off tabulka

| Kritérium | Trvalá role | PIM | JIT VM Access | Custom RBAC |
|---|---|---|---|---|
| Bezpečnost | ❌ Nízká | ✅ Vysoká | ✅ Vysoká | Střední |
| Složitost nastavení | ✅ Snadné | Střední | Střední | Střední |
| Audit trail | Částečný | ✅ Plný | ✅ Plný | Částečný |
| Potřeba Entra ID P2 licence | ❌ | ✅ Ano | ❌ | ❌ |
| Vhodné pro produkci | ❌ | ✅ | ✅ (pro VM) | Podmíněně |

### Doporučení
- **Produkce, compliance požadavky**: PIM (ideálně kombinace s JIT pro VM)
- **Malá firma bez P2 licence**: Custom RBAC s co nejužším scope
- **Přístup pouze na VM**: JIT VM Access

---

## 34. Jak škálovat AKS node pool – Cluster Autoscaler vs Karpenter

### Otázka
AKS cluster potřebuje automaticky škálovat nody. Použiješ Cluster Autoscaler nebo Karpenter? Jaké jsou rozdíly?

### Možnosti řešení

**Varianta A – Cluster Autoscaler (CA)**
Nativně integrovaný v AKS, spravovaný Microsoftem. Škáluje node pooly definované předem (VM SKU je fixní na node pool). Robustní, prověřený, jednoduchý na konfiguraci.

**Varianta B – Karpenter**
Open-source projekt (původně AWS, port pro Azure). Škáluje přímo na úrovni jednotlivých nodů bez předem definovaných node poolů. Vybírá nejlevnější dostupné VM SKU podle aktuálních požadavků podů v reálném čase. Rychlejší reakce na škálování.

### Trade-off tabulka

| Kritérium | Cluster Autoscaler | Karpenter |
|---|---|---|
| Integrace s AKS | ✅ Nativní, managed | Komunitní, nutná instalace |
| Flexibilita VM SKU | ❌ Fixní per node pool | ✅ Dynamická volba |
| Rychlost škálování | Střední (minuty) | ✅ Rychlejší |
| Cost optimalizace (Spot) | Částečně | ✅ Automaticky volí nejlevnější |
| Zralost pro Azure | ✅ Produkčně prověřený | Stále se vyvíjí (2024–2026) |
| Složitost konfigurace | Nízká | Střední–Vysoká |

### Doporučení
- **Stabilní produkce, jednoduchá správa**: Cluster Autoscaler
- **Cost-optimized workloady, smíšené VM typy, Spot instance**: Karpenter (pokud tým má zkušenost s Kubernetes)

---

## 35. Jak publikovat API na internet bezpečně?

### Otázka
Zákazník chce vystavit backend API na internet. Jaké vrstvy zabezpečení a publikování zvážíš?

### Možnosti řešení

**Varianta A – Přímý Load Balancer + NSG**
Nejjednodušší, nejlevnější. Bez WAF, bez rate limitingu, bez API management. Vhodné jen pro interní nebo testovací API.

**Varianta B – Application Gateway + WAF**
L7 balancer s WAF politikami (OWASP ruleset). SSL terminace, ochrana před SQL injection, XSS a dalšími útoky. Regionální řešení.

**Varianta C – Azure API Management (APIM)**
Plná API gateway vrstva: autentizace (OAuth, API key, JWT), rate limiting, throttling, caching, developer portal, versioning a transformace requestů. Lze kombinovat s Application Gateway.

**Varianta D – Azure Front Door + WAF**
Globální entry point s CDN, WAF, anycast routingem a failoverem mezi regiony. Vhodné pro globální aplikace s uživateli v různých zemích.

### Trade-off tabulka

| Kritérium | Load Balancer | App Gateway + WAF | APIM | Front Door + WAF |
|---|---|---|---|---|
| WAF ochrana | ❌ | ✅ | Částečná | ✅ |
| Rate limiting / throttling | ❌ | ❌ | ✅ | Částečný |
| Globální distribuce | ❌ | ❌ | ❌ | ✅ |
| Cena | ✅ Nízká | Střední | ❌ Vysoká | Střední |
| Developer portal pro API | ❌ | ❌ | ✅ | ❌ |
| Vhodné pro B2B API | ❌ | Částečně | ✅ | Částečně |

### Doporučení
- **Interní API, dev/test**: Load Balancer
- **Produkce, jedno-regionální**: Application Gateway + WAF
- **B2B API produkt s verzováním**: APIM + Application Gateway
- **Globální uživatelé, CDN**: Front Door + WAF

---

## 36. Jak spravovat secrety v CI/CD pipeline?

### Otázka
GitHub Actions pipeline potřebuje přístup k Azure SQL connection stringu a ACR. Jak bezpečně spravovat tyto credentials?

### Možnosti řešení

**Varianta A – GitHub Secrets (statické)**
Connection string uložen jako GitHub Secret. Jednoduchý, ale secret je statický, manuálně rotovaný a viditelný adminem repozitáře.

**Varianta B – OIDC federation (Workload Identity)**
Pipeline se přihlásí do Azure bez jakéhokoliv uloženého secretu přes OIDC token exchange. Managed Identity v Azure přijme token z GitHub OIDC issuer. Žádný long-lived secret.

**Varianta C – Key Vault reference v pipeline**
Pipeline si za běhu stáhne secret z Key Vault přes Service Principal nebo Managed Identity. Secret centrálně v Key Vault, rotuje se na jednom místě.

**Varianta D – Azure DevOps Variable Groups + Key Vault link**
Pro Azure DevOps pipelines: Variable Group propojená s Key Vault automaticky načítá secrets před spuštěním pipeline. Transparentní pro pipeline autory.

### Trade-off tabulka

| Kritérium | GitHub Secrets | OIDC federation | Key Vault v pipeline | ADO + KV link |
|---|---|---|---|---|
| Long-lived secret | ❌ Ano | ✅ Žádný | Částečně (SP) | Částečně |
| Rotace secretů | Manuální | Automatická | ✅ Centrální | ✅ Centrální |
| Komplexita nastavení | ✅ Snadné | Střední | Střední | Snadné (ADO) |
| Audit přístupů | Omezený | ✅ Entra ID log | ✅ Key Vault log | ✅ |
| Vhodné pro GitHub Actions | ✅ | ✅ (doporučeno) | ✅ | ❌ (ADO) |

### Doporučení
- **Nový projekt na GitHub**: OIDC federation + pro app secrety Key Vault reference
- **Azure DevOps**: Variable Groups s Key Vault linkem
- **Rychlý start, malý projekt**: GitHub Secrets (ale s plánem migrace)

---

## 37. Jak logovat a monitorovat AKS cluster?

### Otázka
Potřebuješ monitoring AKS clusteru – logy z podů, metriky nodů a alerting. Jaký stack zvolíš?

### Možnosti řešení

**Varianta A – Azure Monitor + Log Analytics + Container Insights**
Nativní Azure řešení. Container Insights automaticky sbírá metriky a logy z clusteru do Log Analytics. Správa přes Azure Portal, dotazy přes KQL. Bez nutnosti instalovat cokoliv extra.

**Varianta B – Prometheus + Grafana (self-managed)**
Open-source stack deployovaný přímo do clusteru. Plná kontrola, žádné náklady za ingestion dat, bohatý ekosystém dashboardů. Vyžaduje správu, storage pro metriky (Thanos nebo Mimir pro long-term).

**Varianta C – Azure Managed Prometheus + Managed Grafana**
Azure spravuje Prometheus i Grafanu – bez nutnosti správy storage nebo upgradů. Integrované s Azure Monitor. Vhodný kompromis mezi kontrolou a managed komfortem.

**Varianta D – Datadog / Dynatrace (SaaS třetí strany)**
Bohaté funkce, APM, distributed tracing, AI anomaly detection. Vysoká cena, ale minimální provozní náklady. Vhodné pro velké enterprise.

### Trade-off tabulka

| Kritérium | Container Insights | Prometheus + Grafana | Managed Prom+Grafana | Datadog |
|---|---|---|---|---|
| Správa infrastruktury | ✅ Žádná | ❌ Nutná | ✅ Žádná | ✅ Žádná |
| Cena | Střední (ingestion) | ✅ Nízká | Střední | ❌ Vysoká |
| Flexibilita dashboardů | Střední | ✅ Vysoká | ✅ Vysoká | ✅ Vysoká |
| Native Azure integrace | ✅ | ❌ | ✅ | Částečná |
| Long-term metric storage | Přes ADX | Nutno řešit | ✅ Managed | ✅ |

### Doporučení
- **Čistě Azure stack, jednoduchá správa**: Container Insights + Managed Grafana
- **Open-source first, cost-conscious**: Prometheus + Grafana s Thanosem
- **Enterprise, APM potřeba**: Datadog nebo Dynatrace

---

## 38. Jak řešit multi-environment deployment (dev/staging/prod)?

### Otázka
Jak navrhnout izolaci prostředí dev, staging a prod v Azure z pohledu subscriptions, resource groups a přístupu?

### Možnosti řešení

**Varianta A – Vše v jedné subscription, odděleno resource groups**
Nejjednodušší, nejlevnější. Chybí ale tvrdá izolace – chyba v policy nebo RBAC může ovlivnit všechna prostředí. Vhodné pro malé týmy nebo startupy.

**Varianta B – Subscription per environment**
Každé prostředí má vlastní subscription. Tvrdá izolace billing, quotas, RBAC a policy na úrovni subscriptions. Doporučovaný enterprise přístup. Management přes Management Groups.

**Varianta C – Subscription per tým/produkt (Landing Zone model)**
Azure Landing Zone metodika – každý produkt nebo tým dostane vlastní subscription. Horizontální škálování bez bottlenecků sdílené subscription. Ideální pro velké organizace s desítkami týmů.

### Trade-off tabulka

| Kritérium | Jedna subscription | Sub per environment | Landing Zone |
|---|---|---|---|
| Izolace prostředí | ❌ Slabá | ✅ Silná | ✅ Silná |
| Správa nákladů (billing) | Složitá | ✅ Přehledná | ✅ Přehledná |
| Quota limity | Sdílené | Oddělené | Oddělené |
| Komplexita správy | ✅ Nízká | Střední | ❌ Vysoká |
| Vhodné pro | Startup, POC | SMB, Enterprise | Velký Enterprise |

### Doporučení
- **Startup, malý tým**: Jedna subscription + oddělené resource groups s jasnými naming conventions
- **Střední firma**: Subscription per environment (dev/staging/prod)
- **Velká organizace**: Azure Landing Zone model s Management Groups

---

## 39. Jak řešit zálohování v Azure?

### Otázka
Zákazník chce zálohy VM, Azure SQL a Azure Files. Jaké nástroje a strategie použiješ?

### Možnosti řešení

**Varianta A – Azure Backup (nativní)**
Centralizovaná zálohovací služba pro VM (disk snapshoty), Azure SQL, Azure Files, AKS volumes i on-premises servery přes MARS agenta. Recovery Services Vault nebo Backup Vault jako centrální úložiště.

**Varianta B – Databázové nativní zálohy**
Azure SQL má built-in automatické zálohy (viz otázka 17). PostgreSQL Flexible Server také. Stačí správně nastavit retention a geo-redundancy bez nutnosti Azure Backup.

**Varianta C – Snapshoty + lifecycle management**
Pro VM disky manuální nebo scheduled snapshoty přes Azure Policy. Levnější než Azure Backup, ale bez centrálního přehledu a složitější restore.

### Trade-off tabulka

| Kritérium | Azure Backup | Nativní DB zálohy | Snapshoty |
|---|---|---|---|
| Centrální správa | ✅ | ❌ Rozptýleno | ❌ |
| Cena | Střední | ✅ Zahrnuto v DB | ✅ Nízká |
| Point-in-time restore | ✅ | ✅ (DB) | ❌ Omezeno |
| Cross-region restore | ✅ | ✅ (Geo SQL) | Manuálně |
| Pokrytí (VM, DB, Files) | ✅ Vše | Jen DB | Jen disky |

### Doporučení
- **Komplexní prostředí, compliance**: Azure Backup jako centrální nástroj + nativní DB zálohy
- **Pouze databáze**: Nativní zálohy s geo-redundancy stačí
- **Cost-first přístup pro dev VM**: Snapshoty s lifecycle policy

---

## 40. Jak řešit síťové propojení on-premises a Azure?

### Otázka
Zákazník potřebuje propojit svojí firemní síť s Azure VNet. Jaké možnosti má a kdy použít VPN vs ExpressRoute?

### Možnosti řešení

**Varianta A – Site-to-Site VPN Gateway**
IPsec VPN tunel přes veřejný internet. Snadné nastavení, nižší cena, dostupné rychle. Latence závislá na internetu, sdílená bandwidth. Vhodné pro menší datové toky nebo zálohu pro ExpressRoute.

**Varianta B – Azure ExpressRoute**
Privátní fyzické propojení přes partnera (T-Systems, CEGEKA, O2 v CZ). Garantovaná bandwidth, nízká latence, bez přechodu přes internet. Drahé a časově náročné na zřízení (týdny až měsíce).

**Varianta C – ExpressRoute + VPN jako failover**
Kombinace pro maximum reliability. ExpressRoute je primární cesta, VPN slouží jako záložní při výpadku ExpressRoute okruhu.

**Varianta D – Azure Virtual WAN**
Hub-and-spoke architektura pro velké organizace s mnoha pobočkami. Automatizuje routing mezi VNety, VPN a ExpressRoute okruhy. Spravováno Microsoftem.

### Trade-off tabulka

| Kritérium | Site-to-Site VPN | ExpressRoute | ER + VPN failover | Virtual WAN |
|---|---|---|---|---|
| Cena | ✅ Nízká | ❌ Vysoká | ❌ Nejvyšší | Střední–Vysoká |
| Latence | Střední (internet) | ✅ Nízká, garantovaná | ✅ Nízká | ✅ Nízká |
| Bandwidth | Až 10 Gbps | Až 100 Gbps | Kombinovaná | Škálovatelná |
| Čas zřízení | Hodiny | Týdny–měsíce | Kombinovaný | Týdny |
| SLA | 99.9 % | 99.95 % | 99.99 % | 99.95 % |
| Vhodné pro | SMB, dev, záloha | Enterprise, citlivá data | Mission-critical | Multi-branch |

### Doporučení
- **Malá firma, dev prostředí nebo záloha**: Site-to-Site VPN
- **Enterprise, citlivá data, nízká latence**: ExpressRoute
- **Mission-critical, nulová tolerance výpadku**: ExpressRoute + VPN failover
- **Firma s desítkami poboček**: Azure Virtual WAN

---

## Jak trade-offs prezentovat u pohovoru

Nejsilnější odpovědi nezačínají "Použil bych X", ale "Záleží na kontextu – klíčové otázky jsou: jaký je budget, jaká jsou SLA požadavky a jak velký je tým pro správu." Tím kandidát ukáže, že přemýšlí jako architekt, ne jen technik. Po identifikaci kontextu pak přijde konkrétní doporučení s odůvodněním.


## 41. Jak chránit Azure Storage Account před neautorizovaným přístupem?

### Otázka
Zákazník má Storage Account s citlivými daty. Jak zajistíš, že k němu nikdo nezíská neautorizovaný přístup?

### Možnosti řešení

**Varianta A – Zakázat public access + Shared Access Signature (SAS)**
Zakázat anonymous public access a používat SAS tokeny s omezenou platností pro přístup klientů. Jednoduché, ale SAS tokeny mohou uniknout a těžko se revokují před expirací.

**Varianta B – Private Endpoint + RBAC**
Zakázat veřejný přístup úplně, přidat Private Endpoint do VNetu a přístup řídit výhradně přes Entra ID RBAC (role Storage Blob Data Reader/Contributor). Žádné sdílené klíče ani SAS tokeny v kódu.

**Varianta C – Service Endpoint + vybraná IP pravidla**
Levnější alternativa k Private Endpointu. Přístup omezen na konkrétní VNet subnet nebo IP rozsahy. Storage je stále na veřejné IP, ale firewall povolí jen whitelisted zdroje.

**Varianta D – Defender for Storage + Microsoft Sentinel**
Přidává aktivní detekci anomálií (neobvyklý přístup, exfiltrace dat, malware upload) a napojení na SIEM pro incident response.

### Trade-off tabulka

| Kritérium | SAS tokeny | Private Endpoint + RBAC | Service Endpoint | Defender for Storage |
|---|---|---|---|---|
| Riziko úniku credentials | ❌ Střední | ✅ Žádné | Střední | N/A (doplněk) |
| Složitost nastavení | ✅ Nízká | Střední | ✅ Nízká | ✅ Snadné |
| Revokace přístupu | ❌ Obtížná | ✅ Okamžitá | ✅ Okamžitá | N/A |
| Cena | ✅ Zdarma | Střední | ✅ Zdarma | Střední |
| Auditovatelnost | Omezená | ✅ Plná (Entra ID) | Střední | ✅ Plná |

### Doporučení
- **Produkce s citlivými daty**: Private Endpoint + RBAC + Defender for Storage
- **Dev/test nebo externí partneři**: SAS tokeny s krátkou platností a IP omezením
- **Kompromis cena/bezpečnost**: Service Endpoint + RBAC

---

## 42. Jak řešit certificate rotation – automaticky vs manuálně?

### Otázka
Zákazník má 15 certifikátů na různých aplikacích. Jak navrhnout lifecycle management certifikátů, aby nedocházelo k výpadkům kvůli expiraci?

### Možnosti řešení

**Varianta A – Manuální správa a kalendářové připomínky**
Nejrozšířenější přístup v malých firmách. Administrátor obnoví certifikát ručně, nahraje ho na aplikace. Vysoké riziko přehlédnutí, zejména při velkém počtu certifikátů.

**Varianta B – Azure Key Vault + automatická obnova přes integrovanou CA**
Key Vault umí automaticky obnovovat certifikáty přes DigiCert nebo GlobalSign (integrované CA). Certifikát se obnoví X dní před expirací bez lidského zásahu. Aplikace si stahují vždy aktuální verzi přes Key Vault reference.

**Varianta C – cert-manager v Kubernetes**
Pro AKS workloady: cert-manager automaticky vydává a obnovuje certifikáty přes Let's Encrypt nebo interní CA. Certifikát žije jako Kubernetes Secret a obnovuje se bez restartu aplikace (s PKCS#11 nebo CSI driver).

**Varianta D – Azure Monitor alert na expiraci + Key Vault event**
Když automatická obnova není možná (vlastní PKI nebo starší systémy), nastaví se alert 60 a 30 dní před expirací přes Key Vault Events → Event Grid → Action Group s emailem nebo ticketem.

### Trade-off tabulka

| Kritérium | Manuální | Key Vault auto-renew | cert-manager | Alert + manuální |
|---|---|---|---|---|
| Riziko výpadku z expirace | ❌ Vysoké | ✅ Minimální | ✅ Minimální | Střední |
| Vhodné pro Kubernetes | ❌ | Částečně | ✅ | Částečně |
| Potřeba integrované CA | N/A | ✅ DigiCert/GlobalSign | ✅ Let's Encrypt / vlastní | ❌ |
| Cena CA | Nízká | Střední (komerční CA) | ✅ Zdarma (LE) | Nízká |
| Vhodné pro on-prem nebo starší systémy | ✅ | ❌ | ❌ | ✅ |

### Doporučení
- **Azure PaaS aplikace**: Key Vault auto-renew s DigiCert nebo GlobalSign
- **AKS workloady**: cert-manager s Let's Encrypt nebo interní CA
- **Hybridní/starší systémy**: Event Grid alert + Key Vault + automatický ticket do helpdesku

---

## 43. Jak detekovat a reagovat na bezpečnostní incident v Azure?

### Otázka
Zákazník hlásí, že jim někdo přihlásil z neznámého místa do Azure Portal a možná provedl změny v infrastruktuře. Jaký bude tvůj postup?

### Možnosti řešení

**Krok 1 – Zjistit co se stalo**
- Azure AD Sign-in logs v Entra ID: zjistím kdo, kdy, odkud a z jakého zařízení se přihlásil
- Azure Activity Log: jaké změny byly provedeny v subscription po daném přihlášení (create, delete, update)
- Microsoft Defender for Cloud: aktivní alerting na podezřelé aktivity

**Krok 2 – Izolovat hrozbu**
- Okamžitě resetovat heslo a invalidovat všechny sessions kompromitovaného účtu (Entra ID → Revoke sessions)
- Zkontrolovat a odvolat případné nové RBAC přiřazení nebo Service Principals vytvořených útočníkem
- Pokud byl vytvořen nový resource, izolovat ho nebo smazat

**Krok 3 – Zjistit rozsah škod**
- Zkontrolovat všechny resources v subscription na neočekávané změny
- Zkontrolovat Key Vault access logy – byly přečteny nebo exportovány secrety?
- Zkontrolovat Storage Account logy – byl exfiltrovaný data?

**Krok 4 – Preventivní opatření**
- Zapnout MFA pro všechny admin účty přes Conditional Access
- Aktivovat Privileged Identity Management – žádné trvalé Owner role
- Zapnout Microsoft Sentinel pro SIEM/SOAR s automatickými response playbooks

### Trade-off tabulka – reactive vs proactive přístup

| Přístup | Reactive (po incidentu) | Proactive (Defender + Sentinel) |
|---|---|---|
| Cena | ✅ Nízká | Střední–Vysoká |
| Čas detekce incidentu | Hodiny–dny | Minuty |
| Automatická response | ❌ | ✅ SOAR playbooks |
| Vhodné pro | Malé firmy | Enterprise, compliance |

---

## 44. Jak navrhnout zero-trust přístup k Azure resources?

### Otázka
Zákazník chce implementovat zero-trust model pro přístup na Azure resources. Jaké komponenty použiješ?

### Možnosti řešení

**Pilíř 1 – Identita**
Conditional Access s MFA pro každý přístup mimo firemní síť. PIM pro privilegované role. Pravidelné access reviews v Entra ID pro automatické odebírání nepoužívaných přístupů.

**Pilíř 2 – Zařízení**
Intune device compliance policy – přístup do Azure Portalu jen z zařízení s aktuálními patchy a šifrováním disku. Conditional Access podmínka na Intune compliance status.

**Pilíř 3 – Síť**
Žádná implicitní důvěra na základě IP nebo síťové lokace. Private Endpointy pro PaaS, NSG s deny-all defaults, Azure Firewall pro inspekci east-west provozu.

**Pilíř 4 – Aplikace a data**
Microsoft Defender for Cloud Apps (MCAS) pro detekci anomálií v SaaS. Defender for Storage a Defender for SQL pro detekci neobvyklých přístupů k datům.

### Trade-off tabulka

| Komponenta | Cena | Složitost | Bezpečnostní přínos |
|---|---|---|---|
| Conditional Access + MFA | Střední (P1) | ✅ Nízká | ✅ Vysoký |
| PIM | Střední (P2) | Střední | ✅ Vysoký |
| Intune compliance | Střední | Střední | Střední |
| Private Endpoints všude | Střední | Střední | ✅ Vysoký |
| Sentinel + SOAR | ❌ Vysoká | ❌ Vysoká | ✅ Nejvyšší |

### Doporučení
- **Quick wins (nízká cena, vysoký přínos)**: Conditional Access + MFA + PIM
- **Full zero-trust**: Postupná implementace všech pilířů, začít od identity

---

## 45. Jak navrhnout multi-region aplikaci v Azure?

### Otázka
Zákazník potřebuje aplikaci dostupnou i při výpadku celého Azure regionu. Jak to navrhnout?

### Možnosti řešení

**Varianta A – Active-Passive (warm standby)**
Primární region obsluhuje veškerý provoz, sekundární region je připravený, ale nečinný. Při výpadku se přepne traffic přes Azure Traffic Manager nebo Front Door. Nižší cena, ale RTO v řádu minut.

**Varianta B – Active-Active**
Oba regiony obsluhují provoz souběžně, Front Door nebo Traffic Manager distribuuje uživatele na nejbližší region. Nulové RTO, ale dvojnásobná cena a složitější synchronizace dat.

**Varianta C – Active-Passive (cold standby)**
Sekundární region je minimálně provisionovaný nebo zcela vypnutý, spouští se jen při disaster recovery. Nejnižší cena, ale nejvyšší RTO (desítky minut až hodiny).

### Trade-off tabulka

| Kritérium | Active-Passive (warm) | Active-Active | Active-Passive (cold) |
|---|---|---|---|
| RTO | Minuty | ✅ Téměř nulové | Desítky minut |
| RPO | Sekundy–minuty | ✅ Sekundy | Minuty–hodiny |
| Cena | Střední | ❌ Dvojnásobná | ✅ Nejnižší |
| Složitost | Střední | ❌ Vysoká | ✅ Nízká |
| Vhodné pro | Většina produkce | Mission-critical, e-commerce | Dev, nekritické systémy |

### Klíčové komponenty
- **Azure Traffic Manager nebo Front Door** pro globální DNS routing a health-based failover
- **Azure SQL Failover Groups** pro automatický databázový failover
- **Azure Site Recovery** pro VM replikaci
- **Geo-redundant Storage (GRS)** pro data

---

## 46. Jak spravovat náklady v multi-subscription Enterprise prostředí?

### Otázka
Firma má 20 subscriptions, různé týmy, různé projekty. Jak nastavit cost governance?

### Možnosti řešení

**Varianta A – Azure Cost Management + tagging**
Centrální přehled nákladů přes Azure Cost Management s breakdownem podle tagů (projekt, tým, prostředí). Budget alerting na úrovni subscription nebo resource group.

**Varianta B – Management Groups + Policy pro povinné tagy**
Azure Policy vynucuje povinné tagy na všech resources. Bez tagu nelze resource vytvořit. Hierarchie Management Groups umožní delegovat billing na business unit úrovni.

**Varianta C – Azure FinOps s rezervacemi a Savings Plans**
Reserved Instances pro předvídatelné VM workloady (1 nebo 3 roky = 30–72 % úspora). Azure Savings Plans pro flexibilnější compute. Spot instances pro batch/dev workloady.

**Varianta D – Showback / Chargeback model**
Automatické reporty v Cost Management exportované do Power BI nebo Azure Storage. Každý tým dostane měsíční přehled svých nákladů. Chargeback = fakturování interním týmům.

### Trade-off tabulka

| Přístup | Komplexita | Úspora | Vhodné pro |
|---|---|---|---|
| Tagging + budgety | ✅ Nízká | Střední | Všechny firmy |
| Policy vynucení tagů | Střední | Střední | SMB, Enterprise |
| Reserved Instances | Střední | ✅ 30–72 % | Stabilní workloady |
| Spot instances | Střední | ✅ Až 90 % | Batch, dev, CI/CD |
| FinOps + showback | ❌ Vysoká | ✅ Vysoká | Velký Enterprise |

---

## 47. Jak navrhnout autentizaci pro veřejnou webovou aplikaci v Azure?

### Otázka
Zákazník buduje B2C webovou aplikaci. Uživatelé se mají přihlašovat přes email, Google nebo Microsoft účet. Jak to navrhnout?

### Možnosti řešení

**Varianta A – Azure AD B2C**
Spravovaná identitní služba pro zákazníky. Podporuje social login (Google, Facebook, Apple, Microsoft), vlastní UI přihlašovacích stránek, MFA, SSPR a JWT tokeny pro API. Oddělená od firemního Entra ID.

**Varianta B – Microsoft Entra External ID (nástupce B2C)**
Moderní náhrada za B2C, lépe integrovaná do Entra ID ekosystému. Jednodušší konfigurace, podpora OIDC/OAuth 2.0, guest uživatelé nebo zákaznické účty v jednom tenantovi.

**Varianta C – Vlastní autentizace s App Service Easy Auth**
App Service má built-in Easy Auth, který přidá autentizaci přes Entra ID, Google, Facebook nebo GitHub bez psaní kódu. Vhodné pro jednoduché scénáře, ale limitované na podporované providery a chybí pokročilé features.

**Varianta D – Open-source (Keycloak na AKS)**
Plná kontrola, žádná vendor lock-in, bohaté features (federation, custom flows). Vyžaduje ale správu infrastruktury, upgradů a high availability.

### Trade-off tabulka

| Kritérium | Azure AD B2C | Entra External ID | Easy Auth | Keycloak |
|---|---|---|---|---|
| Správa infrastruktury | ✅ Žádná | ✅ Žádná | ✅ Žádná | ❌ Nutná |
| Social login | ✅ | ✅ | Omezené | ✅ |
| Cena (MAU model) | Střední | Střední | ✅ Zahrnuto | ✅ Nízká |
| Vlastní UI | ✅ | ✅ | ❌ Omezené | ✅ |
| Vendor lock-in | Střední | Střední | Střední | ✅ Žádný |

### Doporučení
- **Nová B2C aplikace v Azure**: Entra External ID (moderní, jednodušší)
- **Stávající projekt na B2C**: Pokračovat v B2C, migrace není urgentní
- **Full kontrola, on-prem nebo multi-cloud**: Keycloak

---

## 48. Jak řešit síťovou segmentaci pro PCI-DSS compliance?

### Otázka
Zákazník musí splnit PCI-DSS a cardholder data nesmí být přístupná z jiných systémů. Jak navrhnout síťovou segmentaci v Azure?

### Možnosti řešení

**Základní principy PCI-DSS pro Azure síť:**
- Cardholder Data Environment (CDE) musí být izolováno od ostatních systémů
- Veškerý provoz do/z CDE musí procházet firewallem
- Musí existovat auditní log veškerého přístupu

**Navržená architektura:**

```
Internet → Azure Front Door (WAF) → App Gateway (WAF)
                                          ↓
                               [App Subnet - NSG]
                                          ↓
                               Azure Firewall (inspect)
                                          ↓
                               [CDE Subnet - NSG]
                               Azure SQL (Private Endpoint)
                               Key Vault (Private Endpoint)
```

**Konkrétní opatření:**
- CDE v dedikovaném subnetu nebo subscription s přísným NSG (deny all, allow only specific rules)
- Azure Firewall mezi App a CDE subnetem s loggingem všech toků
- Private Endpoints pro SQL a Key Vault
- Defender for SQL pro detekci SQL injection a anomálií
- Log Analytics + Microsoft Sentinel pro audit logs (nutné pro PCI-DSS)
- Azure Policy pro enforcement – žádný resource v CDE nesmí mít veřejnou IP

### Trade-off
Přísná segmentace zvyšuje latenci a komplexitu. Proto je důležité dobře navrhnout, co skutečně patří do CDE scope a co ne – čím menší scope, tím jednodušší compliance.

---

## 49. Jak upgradovat AKS cluster bez výpadku?

### Otázka
Máš produkční AKS cluster na starší verzi Kubernetes. Jak provést upgrade bez výpadku aplikací?

### Možnosti řešení

**Varianta A – In-place upgrade přes az aks upgrade**
Azure postupně upgraduje node pooly – jeden node cordon+drain, upgraduje, vrátí zpět. Aplikace se musí zvládnout přesunout na zbývající nody. Riziko: pokud je cluster plně vytížen nebo aplikace nemá PodDisruptionBudget, může dojít k výpadku.

**Varianta B – Blue-green upgrade (nový node pool)**
Vytvoří se nový node pool s novou verzí K8s. Workloady se postupně přesunou přes taint/toleration nebo node selector. Starý pool se po ověření smaže. Dražší (dvojnásobné nody po dobu migrace), ale bezpečnější.

**Varianta C – Nový cluster (blue-green cluster)**
Celý nový cluster s novou verzí. Traffic se přepne přes Front Door nebo Traffic Manager po ověření. Nejvyšší bezpečnost, ale nejvyšší cena a komplexita (registry, secrets, networking).

### Trade-off tabulka

| Kritérium | In-place upgrade | Nový node pool | Nový cluster |
|---|---|---|---|
| Riziko výpadku | Střední | ✅ Nízké | ✅ Minimální |
| Cena | ✅ Nízká | Střední | ❌ Vysoká |
| Složitost | ✅ Nízká | Střední | ❌ Vysoká |
| Rollback | Obtížný | ✅ Snadný | ✅ Snadný |
| Vhodné pro | Dev, ne-kritické | Produkce | Mission-critical |

### Klíčové prerekvizity pro bezpečný upgrade
- **PodDisruptionBudget** na všechny kritické aplikace
- Minimálně 2 repliky každého deploymentu
- Ověřit kompatibilitu API verzí (kubectl deprecations) před upgradem
- Upgradovat vždy po jedné minor verzi (1.27 → 1.28 → 1.29)

---

## 50. Jak navrhnout observability pro microservices v AKS?

### Otázka
Máš 10 microservices v AKS. Zákazník si stěžuje na pomalé odpovědi, ale není jasné který service je bottleneck. Jak to zjistíš a jak navrhnout observability do budoucna?

### Možnosti řešení

**Varianta A – Distributed tracing s Application Insights**
Každý microservice instrumentovaný Application Insights SDK posílá trace ID přes requesty. Azure Monitor Application Map zobrazí vizuálně toky mezi službami a označí které mají vysokou latenci nebo error rate.

**Varianta B – OpenTelemetry + Jaeger nebo Tempo**
Open-source standard pro distributed tracing. Každý service přidá OpenTelemetry SDK (vendor-agnostic). Data jdou do Jaegeru nebo Grafana Tempo. Plná kontrola, žádný vendor lock-in.

**Varianta C – Service Mesh (Istio nebo Linkerd)**
Service mesh přidá observability automaticky na síťové vrstvě bez změny kódu aplikace. Každý request je tracován, metriky (latence, error rate, throughput) dostupné pro každou service-to-service komunikaci. Přidává ale latenci a správní komplexitu.

### Trade-off tabulka

| Kritérium | Application Insights | OpenTelemetry + OSS | Service Mesh |
|---|---|---|---|
| Změna kódu aplikace | Nutná (SDK) | Nutná (SDK) | ✅ Žádná |
| Vendor lock-in | ❌ Azure | ✅ Žádný | ✅ Žádný |
| Správa infrastruktury | ✅ Managed | Střední | ❌ Komplexní |
| Cena | Střední (ingestion) | ✅ Nízká | ✅ Nízká |
| Vizualizace | ✅ App Map | Grafana | Kiali (Istio) |
| Vhodné pro Azure-first | ✅ | Částečně | Částečně |

### Doporučení
- **Azure-first stack, rychlý start**: Application Insights + Application Map
- **Multi-cloud nebo open-source first**: OpenTelemetry + Grafana Tempo
- **Bez změny kódu, pokročilé traffic management**: Istio (ale počítej se správní zátěží)

---

## Jak odpovědi s trade-offs působí u pohovoru

Kandidát, který říká "záleží na situaci" a dokáže přesně říct na čem záleží, působí výrazně zkušeněji než ten, kdo mechanicky vyjmenuje jednu možnost. Klíčem je vždy začít identifikací klíčových omezení (budget, team size, SLA, compliance) a teprve pak přejít k doporučení.

## 51. Jak navrhnout řešení pro zpracování velkého množství zpráv (message queue)?

### Otázka
Aplikace generuje tisíce eventů za sekundu. Backend je nestíhá zpracovávat. Jak to architektonicky vyřešit?

### Možnosti řešení

**Varianta A – Azure Service Bus**
Plnohodnotná message broker služba s frontami (Queues) a tématy (Topics + Subscriptions). Garantované doručení, dead-letter queue, sessions, transakce. Vhodné pro enterprise messaging a command-based systémy.

**Varianta B – Azure Event Hubs**
Streamovací platforma pro miliony eventů za sekundu. Vhodné pro telemetrii, logy, IoT data. Consumer groups umožní paralelní zpracování. Data se ukládají a lze je přehrát zpět (retention).

**Varianta C – Azure Storage Queue**
Nejjednodušší a nejlevnější varianta. Vhodné pro jednoduché async processing bez potřeby ordering nebo dead-letter logiky.

**Varianta D – Azure Event Grid**
Reaktivní event routing, ne streaming. Vhodné pro "někdo něco udělal v Azure" eventy (blob upload, VM start) nebo serverless triggery.

### Trade-off tabulka

| Kritérium | Service Bus | Event Hubs | Storage Queue | Event Grid |
|---|---|---|---|---|
| Throughput | Střední | ✅ Miliony/s | Střední | Střední |
| Garantované doručení | ✅ | ✅ | ✅ | ✅ |
| Dead-letter queue | ✅ | ❌ | ❌ | ✅ |
| Replay / retention | ❌ | ✅ | ❌ | ❌ |
| Cena | Střední | Střední | ✅ Nejnižší | Nízká |
| Vhodné pro | Enterprise messaging | IoT, telemetrie, logy | Jednoduché async | Serverless eventy |

### Doporučení
- **Enterprise aplikace, objednávky, transakce**: Service Bus
- **IoT, telemetrie, log streaming**: Event Hubs
- **Jednoduché task queue**: Storage Queue
- **Serverless reakce na Azure eventy**: Event Grid

---

## 52. Jak navrhnout deployment strategie pro minimalizaci rizika?

### Otázka
Zákazník se bojí nasadit novou verzi aplikace, protože v minulosti měl výpadky. Jaké deployment strategie znáš a kdy je použít?

### Možnosti řešení

**Varianta A – Rolling deployment**
Kubernetes výchozí strategie. Postupně nahrazuje staré pody novými. Část provozu vždy jde na novou verzi, část na starou. Žádné extra resources potřeba.

**Varianta B – Blue-Green deployment**
Dvě identická prostředí (Blue = prod, Green = nová verze). Traffic se přepne najednou. Okamžitý rollback přepnutím zpět. Vyžaduje dvojnásobné resources po dobu deploymentu.

**Varianta C – Canary deployment**
Nová verze dostane malé % trafficu (např. 5 %), zbytek jde na starou. Postupně se zvyšuje při ověření stability. Nejbezpečnější, ale vyžaduje traffic splitting (Ingress, AGIC nebo Flagger).

**Varianta D – A/B testing**
Podobné Canary, ale uživatelé jsou segmentovaní záměrně (např. podle lokace nebo cookie). Vhodné pro feature flagging a UX experimenty.

### Trade-off tabulka

| Kritérium | Rolling | Blue-Green | Canary | A/B Testing |
|---|---|---|---|---|
| Extra resources | ✅ Minimální | ❌ Dvojnásobné | Střední | Střední |
| Rychlost rollbacku | Pomalá | ✅ Okamžitá | Střední | Střední |
| Riziko při deploymentu | Střední | ✅ Nízké | ✅ Nejnižší | ✅ Nízké |
| Složitost | ✅ Nízká | Střední | ❌ Vysoká | ❌ Vysoká |
| Vhodné pro | Standardní deploymenty | Kritické systémy | Velké risky | Feature testing |

---

## 53. Jak zabezpečit AKS cluster na síťové úrovni?

### Otázka
Jak nastavit AKS cluster tak, aby byl co nejbezpečnější z pohledu sítě? Co jsou klíčové komponenty?

### Vrstvy zabezpečení

**Vrstva 1 – Privátní cluster**
API server je dostupný pouze z privátní IP adresy v daném VNetu nebo přes privátní peering. Žádný veřejný přístup na Kubernetes API.

**Vrstva 2 – Network Policy**
Kubernetes Network Policy (nebo Calico/Azure NPM) definuje pravidla, které pody spolu mohou komunikovat. Výchozí pravidlo: deny all, explicitně povolovat jen potřebné.

**Vrstva 3 – Azure CNI vs Kubenet**
Azure CNI přiděluje každému podu reálnou IP z VNetu – pody jsou přímo viditelné v síti a lze na ně aplikovat NSG. Kubenet používá NAT, pody mají overlay adresy.

**Vrstva 4 – Egress přes Azure Firewall**
Veškerý odchozí provoz z clusteru přes Azure Firewall s FQDN pravidly. Tím je vidět a kontrolováno, kam pody přistupují.

### Trade-off tabulka

| Opatření | Bezpečnostní přínos | Složitost | Cena |
|---|---|---|---|
| Privátní cluster | ✅ Vysoký | Střední | ✅ Nízká |
| Network Policy | ✅ Vysoký | Střední | ✅ Nízká |
| Azure CNI | Střední | Střední | ✅ Nízká |
| Egress přes Firewall | ✅ Vysoký | Střední | Střední |
| Defender for Containers | ✅ Vysoký | ✅ Nízká | Střední |

---

## 54. Jak navrhnout přístup k Azure pro on-premises aplikace?

### Otázka
On-premises aplikace potřebuje číst data z Azure Storage a zapisovat do Azure SQL. Jak to nastavit bezpečně bez ukládání credentials?

### Možnosti řešení

**Varianta A – Service Principal + secret v trezoru**
Aplikace používá service principal, secret je uložen v on-premises trezoru nebo HSM. Nutná správa rotace.

**Varianta B – Service Principal + certifikát místo secretu**
Certifikát je bezpečnější než secret – kratší platnost, složitější krádež. Stále ale nutná správa.

**Varianta C – Federated Identity (Workload Identity Federation)**
On-premises systém vydá OIDC token, který Azure vymění za Entra ID token. Žádný long-lived secret. Funguje pro GitHub Actions, Kubernetes, AWS a jiné OIDC issuery.

**Varianta D – Azure Arc + Managed Identity**
Pokud je on-prem server registrovaný v Azure Arc, může dostat Managed Identity a přistupovat k Azure resources jako Azure VM. Nejčistší řešení bez credentials.

### Doporučení
- **Server registrovaný v Azure Arc**: Managed Identity přes Arc
- **Moderní CI/CD nebo Kubernetes on-prem**: Workload Identity Federation
- **Starší systém bez OIDC podpory**: Service Principal + certifikát

---

## 55. Jak navrhnout škálování Azure SQL databáze?

### Otázka
Aplikace má výkonnostní problémy s Azure SQL při špičkách. Jak řešit škálování?

### Možnosti řešení

**Varianta A – Scale up (vyšší DTU/vCore tier)**
Nejjednodušší – přejít na vyšší výkonnostní tier. Žádné změny v aplikaci. Cena roste lineárně.

**Varianta B – Read replicas (Geo-replikace)**
Čtecí dotazy přesměrovat na read-only repliku. Snižuje zátěž primárního serveru. Vyžaduje změnu connection stringu v aplikaci nebo query routing.

**Varianta C – Azure SQL Hyperscale tier**
Speciální architektura pro velké databáze (až 100 TB). Odděluje compute a storage, umožní přidat read repliky za sekundy.

**Varianta D – Caching vrstva (Redis)**
Opakované čtecí dotazy cachovat v Azure Cache for Redis. Snižuje počet dotazů na databázi o desítky procent.

**Varianta E – Elastic Pool**
Více databází sdílí jeden pool zdrojů. Vhodné pro SaaS model, kde různé databáze mají špičky v různý čas.

### Doporučení
- **Rychlé řešení, malá aplikace**: Scale up
- **Read-heavy workload**: Read replicas + Redis cache
- **Velká databáze, SaaS**: Hyperscale
- **Multi-tenant SaaS**: Elastic Pool

---

## 56. Co je Azure Policy a jak funguje remediation?

### Otázka
Zákazník chce zajistit, že všechny Storage Accounty v subscriptionu mají zapnuté HTTPS only. Jak to vynutit a co se stane s existujícími resources?

### Policy efekty

- **Audit**: Pouze označí non-compliant resources v reportu, nic nevynutí. Vhodné pro první fázi.
- **Deny**: Zabrání vytvoření nebo úpravě resource bez splnění podmínky. Existující resources neovlivní.
- **Modify**: Automaticky přidá nebo změní property při vytvoření nebo úpravě resource.
- **DeployIfNotExists (DINE)**: Pokud chybí závislý resource, automaticky ho deployuje.

### Postup pro HTTPS-only Storage
1. Nasadit s efektem **Audit** – zmapovat kolik resources není compliant
2. Přejít na **Modify** efekt – nové i upravované resources se automaticky opraví
3. Spustit **remediation task** na existující resources

Remediation task vyžaduje Managed Identity pro Policy assignment s oprávněním na úpravu resources.

---

## 57. Jak navrhnout backup a restore pro AKS workloady?

### Otázka
Zákazník chce zálohovat AKS cluster – nejen data, ale i Kubernetes objekty (deployments, services, configmaps). Jak to řešit?

### Možnosti řešení

**Varianta A – Azure Backup for AKS**
Nativní Azure řešení (GA od 2024). Zálohuje Kubernetes resources (YAML manifesty) i perzistentní volumes přes CSI snapshoty.

**Varianta B – Velero**
Open-source nástroj pro backup Kubernetes resources a volumes. Ukládá do Azure Blob Storage. Podporuje cross-cluster a cross-region restore.

**Varianta C – GitOps (Flux nebo ArgoCD) jako "backup"**
Pokud jsou všechny manifesty v Git repozitáři, cluster lze obnovit apply přes Git. Funguje pro stateless aplikace, ale neřeší data v PersistentVolumes.

### Trade-off tabulka

| Kritérium | Azure Backup for AKS | Velero | GitOps |
|---|---|---|---|
| Správa infrastruktury | ✅ Managed | Střední | ✅ Žádná |
| PV (data) backup | ✅ | ✅ | ❌ |
| Cross-cluster restore | ✅ | ✅ | ✅ |
| Cena | Střední | ✅ Nízká (jen storage) | ✅ Zdarma |
| Zralost | Nová (2024) | ✅ Prověřené | ✅ Prověřené |

### Doporučení
- **Azure-first, jednoduchá správa**: Azure Backup for AKS
- **Open-source, cross-cloud**: Velero
- **Stateless aplikace**: GitOps + Velero jen pro PV

---

## 58. Jak navrhnout logging strategii pro compliance (audit logy)?

### Otázka
Zákazník v regulovaném odvětví potřebuje uchovávat audit logy 7 let a zajistit, že je nikdo nemůže smazat. Jak to technicky zajistit?

### Řešení

**Komponenty:**
- **Azure Activity Log** → exportovat do Log Analytics Workspace nebo Azure Storage
- **Storage Account s immutable blob storage** – nastavit Time-based retention policy (WORM). Žádný uživatel ani admin nemůže smazat blob před uplynutím retention period.
- **Log Analytics Workspace** s nastaveným retention (až 12 let s archivní vrstvou)
- **Diagnostic Settings** na všechny kritické resources → logy do Log Analytics

**Nastavení immutable storage:**
```
Storage Account → Containers → Access Policy
→ Add policy: Time-based retention
→ Retention period: 2557 dní (7 let)
→ Locked policy (po zamčení nejde změnit ani smazat)
```

### Doporučení
- Logy posílat do dvou míst: Log Analytics (pro dotazy a alerting) + immutable Storage (pro compliance archiv)
- Nastavit lifecycle management na Storage pro přesun do Archive tier po 1 roce (úspora nákladů)
- Oddělená subscription nebo resource group pro compliance storage s přísným RBAC

---

## 59. Jak navrhnout Azure infrastrukturu pro AI/ML workloady?

### Otázka
Datový tým chce trénovat ML modely v Azure. Potřebují GPU compute, přístup k datům ze Storage a experimenty logovat. Jaké Azure služby doporučíš?

### Možnosti řešení

**Varianta A – Azure Machine Learning (AzureML)**
Kompletní managed platform: experiment tracking (MLflow integrovaný), managed compute clustery s GPU, model registry, deployment jako online endpoint nebo batch.

**Varianta B – AKS s GPU node pool**
Pro týmy, které preferují Kubernetes a chtějí plnou kontrolu. GPU nody (NV nebo NC series), Jupyter nebo custom kontejnery.

**Varianta C – Azure Databricks**
Apache Spark-based platforma pro big data + ML. Jednotné prostředí pro data engineering i ML. Integrovaný MLflow, notebook prostředí, Delta Lake.

### Trade-off tabulka

| Kritérium | AzureML | AKS + GPU | Databricks |
|---|---|---|---|
| Správa infrastruktury | ✅ Managed | ❌ Nutná | ✅ Managed |
| MLflow / experiment tracking | ✅ Built-in | Manuální | ✅ Built-in |
| Spark / big data | ❌ | ❌ | ✅ |
| Cena | Střední | Střední | ❌ Vysoká |
| Flexibilita | Střední | ✅ Vysoká | Střední |

### Doporučení
- **Enterprise ML tým, Azure-first**: AzureML
- **Stávající Kubernetes infrastruktura**: AKS + GPU node pool
- **Big data + ML dohromady**: Azure Databricks

---

## 60. Jak řešit dependency management v Terraformu pro velký projekt?

### Otázka
Terraform projekt narostl na stovky resources. Plan trvá minuty, apply selhává na timeouty. Jak projekt restrukturalizovat?

### Možnosti řešení

**Varianta A – Rozdělení do modulů**
Logicky seskupit resources do Terraform modulů (networking, compute, database, security). Zlepší čitelnost, ale state je stále jeden velký.

**Varianta B – Rozdělení state souborů (multiple backends)**
Každá vrstva má vlastní state soubor. Výstupy se čtou přes `terraform_remote_state` data source. Plan a apply je výrazně rychlejší.

**Varianta C – Terragrunt**
Wrapper nad Terraformem, který řeší DRY konfiguraci pro více prostředí a automatizuje orchestraci závislostí mezi state soubory.

**Varianta D – OpenTofu (open-source fork Terraformu)**
Pro projekty, které chtějí opustit HashiCorp BSL licenci. API kompatibilní s Terraformem.

### Trade-off tabulka

| Kritérium | Monolitický state | Moduly | Separátní state | Terragrunt |
|---|---|---|---|---|
| Rychlost plan/apply | ❌ Pomalá | Střední | ✅ Rychlá | ✅ Rychlá |
| Složitost správy | ✅ Nízká | Střední | Střední | ❌ Vysoká |
| Bezpečnost (blast radius) | ❌ Vysoký | Střední | ✅ Nízký | ✅ Nízký |
| Vhodné pro | Malé projekty | Střední projekty | Velké projekty | Enterprise |

### Doporučení
- **Malý projekt, 1–2 vývojáři**: Moduly stačí
- **Střední firma**: Separátní state per layer nebo environment
- **Enterprise, desítky prostředí**: Terragrunt

---

## Jak trade-offs prezentovat u pohovoru

Nejsilnější odpovědi nezačínají "Použil bych X", ale "Záleží na kontextu – klíčové otázky jsou: jaký je budget, jaká jsou SLA požadavky a jak velký je tým pro správu." Po identifikaci kontextu pak přijde konkrétní doporučení s odůvodněním.
