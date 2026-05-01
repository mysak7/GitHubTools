# Azure pohovor – třetí sada 10 otázek a vzorové odpovědi

Tato třetí sada pokrývá pokročilejší témata: Key Vault a certifikáty, Terraform v CI/CD, DNS, Traffic Manager, App Gateway vs Front Door, identita workloadů a monitoring zabezpečení.

---

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
