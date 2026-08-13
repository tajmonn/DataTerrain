## 28-Jul-26

Po prostu dawanie dwóch list agentowi, nie przynosi na razie skutków jakie byśmy chcieli.

Nie wiem na ile to jest zależne od modelu, a ile od mojej niewiedzy. 

Do przetestowania: 
- kupiłem 10$ (plus 2.5$ tax **WTH?!**), na **OpenAI** - ale raczej pozostańmy tam na modelach nano, zanim dokładnie ogarnę ile takie zapytania zjadą tokenów itp... (trzeba to przebadać z logfire'em)
- na githubie vstorma jest z przykładami użyty **bielik** (llamowa wersja polska czata, może ona będzie sobie lepiej radziła z polską administracją 😔)
- Zastanawiam się czy nie jest lepszym podejściem wymaganie jako **odpowiedzi listy par indeksów**, z dwóch podanych list, niż kazać mu jakoś inaczej je łączyć. Bo jeżeli 8 sekund mu zajmie zastanawianie się czy trzebnicki i powiat trzebnicki to to samo i należy je połączyć to możemy mieć problem (**godzina na wszystkie powiaty w polsce**) - na pewno trzeba je przekazywać **inaczej niż dependecies**, bo tutaj zaczynam myśleć, że coś chyba nie trafiłem z założeniami jak to ma działać <- OGARNĄĆ!


Nie mam siły już dzisiaj, z tym walczyć, muszę się przewietrzyć i usiąść do tego z czystą głową. Nie mam co innego za bardzo programować poza co najwyżej portfolio Zuzy, ale nie wiem czy powinienem się za to zabierać jak nie mam za bardzo pomysłu w głowie, ani jakiegoś określenia od niej. Tak więc... rolki?

## 13-Aug-26

Orlik chyba faktycznie sobie lepiej radzi.  
Zmieniona filozofia na uzywanie fuzzy zanim to pójdzie do AI - z myślą aby AI było dodatkową opcjonalną funkcją gdy fuzzy już nie daje rady, ale nadal możliwe jest poprawienie go człowiekiem.
Problematyczne na razie ma zadanie. Trzeba mu je ułatwić.
Czasami podaje opcje nie z listy (halucynacje)
Czasami ma problem o to że nie ma przed przymiotnikiem "powiat"
Czasami mu sie udaje czasami nie - karkonoski - Jelenia Góra.
Dodać mu opcje powtórzenia tego albo dodanie agenta ktory bedzie go sprawdzal czy nie poniosło go.