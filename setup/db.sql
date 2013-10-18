CREATE TABLE event (
    eventid integer NOT NULL,
    name character varying(60),
    type character varying(20)
);

-- Family
CREATE TABLE family (
    familyid integer NOT NULL,
    name character varying(200),
    tagnumber integer,
    territory character varying(30)
);

ALTER TABLE ONLY family
    ADD CONSTRAINT family_pkey PRIMARY KEY (familyid);
CREATE INDEX family_number_index ON family USING btree (tagnumber);

-- Person
CREATE TABLE person (
    personid integer NOT NULL,
    name character varying(200),
    family_tag integer,
    tagnumber integer,
    type character varying(40),
    kids_group character varying(40),
    kids_team character varying(40),
    school_year integer,
    dob date,
    medical_info text,
    medical_notes text,
    territory character varying(30),
    firstname character varying(30),
    gender character varying(10),
    marital_status character varying(20),
    lifegroup character varying(60),
    address1 character varying(40),
    address2 character varying(40),
    city character varying(20),
    postcode character varying(20),
    country character varying(20),
    home_phone character varying(40),
    mobile_phone character varying(40),
    email character varying(40)
);

ALTER TABLE ONLY person
    ADD CONSTRAINT person_pkey PRIMARY KEY (personid);
CREATE INDEX person_family_tag_index ON person USING btree (family_tag);
    
-- Registration
CREATE TABLE registration (
    registrationid SERIAL,
    family_tag integer,
    person_tag integer,
    status character varying(20),
    eventid integer,
    event_date date
);

-- Sync log
CREATE TABLE sync (
    syncid SERIAL,
    tablename character varying(20),
    lastsync timestamp without time zone
);

-- Users
CREATE TABLE visitor (
    personid integer,
    username character varying(40),
    password character varying(100),
    name character varying(200),
    access character varying(40)
);

