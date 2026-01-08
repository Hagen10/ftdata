SELECT * FROM dbo.Afstemning
WHERE nummer = 512 AND sagstrinid = 265952
ORDER BY opdateringsdato DESC

-- sagstrin id: 265952 (that's when it was being voted on)

SELECT * FROM dbo.SagstrinDokument
WHERE sagstrinid = 265952
ORDER BY opdateringsdato DESC


-- the one we care about has id 101843
SELECT * FROM dbo.Sag
WHERE nummer = 'B 177' -- You can't really use B 177. You need to use 84443 from emneordsag
AND id = 101843

SELECT * FROM dbo.SagDokument
WHERE sagid = 101843

SELECT COUNT(*) FROM dbo.Emneord

SELECT * FROM dbo.EmneordSag
WHERE sagid = 101843
-- below you find the emneord that is linked to the example case (101843)
SELECT * FROM dbo.Emneord
WHERE id IN ('85674', '33502', '84443', '85521')

-- number of cases that have the borgerforslag topic (84443)
SELECT COUNT(id) FROM dbo.EmneordSag
WHERE emneordid = 84443
-- list of cases that have the borgerforslag topic
SELECT * FROM dbo.EmneordSag
where emneordid = 84443

-- Getting Sag information about all borgerforslag in the Sag table
SELECT * FROM dbo.Sag
INNER JOIN dbo.EmneordSag ON dbo.Sag.id = dbo.EmneordSag.sagid
WHERE dbo.EmneordSag.emneordid = 84443

SELECT * FROM dbo.Sagstrin
WHERE sagid = 101843

SELECT * FROM dbo.Sagstrinstype
-- the vote for our case (voting 10362)
SELECT * FROM dbo.Afstemning
WHERE sagstrinid = 265952
ORDER BY opdateringsdato DESC

SELECT * FROM dbo.Afstemningstype
-- list of 2. behandling voting
SELECT * FROM dbo.Sagstrin
WHERE typeid = 7
ORDER BY dato DESC

-- list of 3. behandling voting (rare cases where 2. behandling leads to more discussions)
SELECT * FROM dbo.Sagstrin
WHERE typeid = 17
ORDER BY dato DESC

-- finding out who voted what on our case 101843 (sagstrin 265952)

SELECT * FROM dbo.Stemmetype
-- all the votes (yes, no, neither or, absent)
SELECT COUNT(id) FROM dbo.Stemme
WHERE afstemningid = 10362
-- joining voters for this vote
SELECT * FROM dbo.Stemme
INNER JOIN dbo.Aktør ON dbo.Stemme.aktørid = dbo.Aktør.id
WHERE dbo.Stemme.afstemningid = 10362

SELECT * FROM dbo.Aktør

-- more specific query only showing interesting information
SELECT * FROM dbo.Stemme
INNER JOIN dbo.Aktør ON dbo.Stemme.aktørid = dbo.Aktør.id
WHERE dbo.Stemme.afstemningid = 10362

-- Query showing the name of the politician and their vote type (ignore last AND to see all votes and not just specific types)
SELECT dbo.Aktør.navn, dbo.Stemmetype.[type] FROM dbo.Aktør
INNER JOIN dbo.Stemme ON dbo.Aktør.id = dbo.Stemme.aktørid
INNER JOIN dbo.Stemmetype ON dbo.Stemme.typeid = dbo.Stemmetype.id
WHERE dbo.Stemme.afstemningid = 10362
AND dbo.Stemmetype.id = 2

-- TO DO: Link Aktør to Party so we can also find information about what the majority of a party voted for
-- I think you need to retrieve it from the bio part in the Aktør table...


-- Counting how many non absent votes each politician has placed
SELECT dbo.Aktør.navn, count(*) AS votes FROM dbo.Aktør
INNER JOIN dbo.Stemme ON dbo.Aktør.id = dbo.Stemme.aktørid
AND dbo.Stemme.typeid != 3
GROUP BY dbo.Aktør.navn
ORDER BY votes DESC

-- 1 For, 2 Imod, 3 Fravær, 4 Hverken eller

-- Sigurd's ID er 20359
SELECT * FROM dbo.Aktør
WHERE dbo.Aktør.fornavn LIKE '%Sigurd%'

SELECT * FROM dbo.AktørType

-- The amount of times that Sigurd voted (not including being absent)
SELECT dbo.Aktør.navn, count(*) AS votes FROM dbo.Aktør
INNER JOIN dbo.Stemme ON dbo.Aktør.id = dbo.Stemme.aktørid
AND dbo.Stemme.typeid != 3
WHERE dbo.Aktør.id = 20359
GROUP BY dbo.Aktør.navn
ORDER BY votes DESC

-- Counts of each of Sigurd's vote types (including absence)
SELECT
    dbo.Aktør.navn,
    SUM(CASE WHEN dbo.Stemme.typeid = 1 THEN 1 ELSE 0 END) AS "for",
    SUM(CASE WHEN dbo.Stemme.typeid = 2 THEN 1 ELSE 0 END) AS "Imod",
    SUM(CASE WHEN dbo.Stemme.typeid = 3 THEN 1 ELSE 0 END) AS "fravær",
    SUM(CASE WHEN dbo.Stemme.typeid = 4 THEN 1 ELSE 0 END) AS "Hverken eller",
    COUNT(*) AS "Total"
FROM dbo.Aktør
INNER JOIN dbo.Stemme ON dbo.Aktør.id = dbo.Stemme.aktørid
WHERE dbo.Aktør.id = 20359
GROUP BY dbo.Aktør.navn


-- All cases that are of type 7 in Sagstrin (2. behandling)
SELECT * FROM dbo.Sag
INNER JOIN dbo.Sagstrin ON dbo.Sag.id = dbo.Sagstrin.sagid
WHERE dbo.Sagstrin.typeid = 7
ORDER BY dbo.Sag.opdateringsdato DESC
--WHERE dbo.Sag.id = 101843

-- Alle sager, som Sigurd har stemt på (eller hvert fraværende)
SELECT * FROM dbo.Sag
INNER JOIN dbo.Sagstrin ON dbo.Sag.id = dbo.Sagstrin.sagid
INNER JOIN dbo.Afstemning ON dbo.Sagstrin.id = dbo.Afstemning.sagstrinid
INNER JOIN dbo.Stemme ON dbo.Afstemning.id = dbo.Stemme.afstemningid
INNER JOIN dbo.Aktør ON dbo.Stemme.aktørid = dbo.Aktør.id
WHERE dbo.Aktør.id = 20359

-- Query med stemmetype og færre kolonner
SELECT dbo.Afstemning.id, dbo.Sag.titel, dbo.Sag.titelkort, dbo.Sag.resume, dbo.Sag.afstemningskonklusion, dbo.Aktør.navn, dbo.Stemmetype.[type] FROM dbo.Sag
INNER JOIN dbo.Sagstrin ON dbo.Sag.id = dbo.Sagstrin.sagid
INNER JOIN dbo.Afstemning ON dbo.Sagstrin.id = dbo.Afstemning.sagstrinid
INNER JOIN dbo.Stemme ON dbo.Afstemning.id = dbo.Stemme.afstemningid
INNER JOIN dbo.Aktør ON dbo.Stemme.aktørid = dbo.Aktør.id
INNER JOIN dbo.Stemmetype ON dbo.Stemme.typeid = dbo.Stemmetype.id
WHERE dbo.Aktør.id = 20359

-- Samme som ovenstående men kun borgerforslagafstemninger
SELECT dbo.Sag.titel, dbo.Sag.resume, dbo.Sag.afstemningskonklusion, dbo.Aktør.navn, dbo.Stemmetype.[type] FROM dbo.Sag
INNER JOIN dbo.Sagstrin ON dbo.Sag.id = dbo.Sagstrin.sagid
INNER JOIN dbo.Afstemning ON dbo.Sagstrin.id = dbo.Afstemning.sagstrinid
INNER JOIN dbo.Stemme ON dbo.Afstemning.id = dbo.Stemme.afstemningid
INNER JOIN dbo.Aktør ON dbo.Stemme.aktørid = dbo.Aktør.id
INNER JOIN dbo.Stemmetype ON dbo.Stemme.typeid = dbo.Stemmetype.id
INNER JOIN dbo.EmneordSag ON dbo.Sag.id = dbo.EmneordSag.sagid
WHERE dbo.Aktør.id = 20359
AND dbo.EmneordSag.emneordid = 84443


-- next challenge: Try to narrow the voting to only include votes done since the last election.
-- Also figure out how to extract party information (this could possibly be done elsewhere like in the service that queries the database using regex)
-- Make a list showing people who vote the most, are the most absent
-- Do men vote more than women? The biografi contains the sex of the person.. If only we could retrieve it somehow
-- which people have voted against the party they belong to and in what cases did they do it?
-- Candidate test ideas: Show the people/parties that you align with the most and the people/parties that you disagree with the most

-- List of all voters, sorted by least absence and most votes given
SELECT
    dbo.Aktør.navn,
    SUM(CASE WHEN dbo.Stemme.typeid = 1 THEN 1 ELSE 0 END) AS "for",
    SUM(CASE WHEN dbo.Stemme.typeid = 2 THEN 1 ELSE 0 END) AS "Imod",
    SUM(CASE WHEN dbo.Stemme.typeid = 3 THEN 1 ELSE 0 END) AS "fravær",
    SUM(CASE WHEN dbo.Stemme.typeid = 4 THEN 1 ELSE 0 END) AS "Hverken eller",
    COUNT(*) AS "Total"
FROM dbo.Aktør
INNER JOIN dbo.Stemme ON dbo.Aktør.id = dbo.Stemme.aktørid
GROUP BY dbo.Aktør.navn
ORDER BY "fravær" ASC, "Total" DESC

SELECT * FROM dbo.Afstemning
WHERE nummer = 533

