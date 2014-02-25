--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: event; Type: TABLE; Schema: public; Owner: cyglffdwsktfeo; Tablespace: 
--

CREATE TABLE event (
    eventid integer NOT NULL,
    name character varying(60),
    type character varying(20),
    externalid character varying(20) NOT NULL
);


ALTER TABLE public.event OWNER TO cyglffdwsktfeo;

--
-- Name: event_eventid_seq; Type: SEQUENCE; Schema: public; Owner: cyglffdwsktfeo
--

CREATE SEQUENCE event_eventid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.event_eventid_seq OWNER TO cyglffdwsktfeo;

--
-- Name: event_eventid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cyglffdwsktfeo
--

ALTER SEQUENCE event_eventid_seq OWNED BY event.eventid;


--
-- Name: family; Type: TABLE; Schema: public; Owner: cyglffdwsktfeo; Tablespace: 
--

CREATE TABLE family (
    familyid integer NOT NULL,
    name character varying(200),
    tagnumber integer,
    territory character varying(30),
    externalid character varying(20)
);


ALTER TABLE public.family OWNER TO cyglffdwsktfeo;

--
-- Name: groups; Type: TABLE; Schema: public; Owner: cyglffdwsktfeo; Tablespace: 
--

CREATE TABLE groups (
    groupsid integer NOT NULL,
    name character varying(40),
    code character varying(20)
);


ALTER TABLE public.groups OWNER TO cyglffdwsktfeo;

--
-- Name: groups_groupsid_seq; Type: SEQUENCE; Schema: public; Owner: cyglffdwsktfeo
--

CREATE SEQUENCE groups_groupsid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.groups_groupsid_seq OWNER TO cyglffdwsktfeo;

--
-- Name: groups_groupsid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cyglffdwsktfeo
--

ALTER SEQUENCE groups_groupsid_seq OWNED BY groups.groupsid;


--
-- Name: membership; Type: TABLE; Schema: public; Owner: cyglffdwsktfeo; Tablespace: 
--

CREATE TABLE membership (
    membershipid integer NOT NULL,
    personid integer NOT NULL,
    groupsid integer NOT NULL
);


ALTER TABLE public.membership OWNER TO cyglffdwsktfeo;

--
-- Name: membership_membershipid_seq; Type: SEQUENCE; Schema: public; Owner: cyglffdwsktfeo
--

CREATE SEQUENCE membership_membershipid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.membership_membershipid_seq OWNER TO cyglffdwsktfeo;

--
-- Name: membership_membershipid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cyglffdwsktfeo
--

ALTER SEQUENCE membership_membershipid_seq OWNED BY membership.membershipid;


--
-- Name: person_personid_seq; Type: SEQUENCE; Schema: public; Owner: cyglffdwsktfeo
--

CREATE SEQUENCE person_personid_seq
    START WITH 2500
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.person_personid_seq OWNER TO cyglffdwsktfeo;

--
-- Name: person; Type: TABLE; Schema: public; Owner: cyglffdwsktfeo; Tablespace: 
--

CREATE TABLE person (
    personid integer DEFAULT nextval('person_personid_seq'::regclass) NOT NULL,
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
    email character varying(40),
    baptised boolean,
    salvation boolean,
    partner boolean,
    key_leader boolean,
    externalid character varying(20)
);


ALTER TABLE public.person OWNER TO cyglffdwsktfeo;

--
-- Name: registration; Type: TABLE; Schema: public; Owner: cyglffdwsktfeo; Tablespace: 
--

CREATE TABLE registration (
    registrationid integer NOT NULL,
    family_tag integer,
    person_tag integer,
    status character varying(20),
    eventid integer,
    event_date date,
    last_modified timestamp without time zone DEFAULT ('now'::text)::date NOT NULL
);


ALTER TABLE public.registration OWNER TO cyglffdwsktfeo;

--
-- Name: registration_registrationid_seq; Type: SEQUENCE; Schema: public; Owner: cyglffdwsktfeo
--

CREATE SEQUENCE registration_registrationid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.registration_registrationid_seq OWNER TO cyglffdwsktfeo;

--
-- Name: registration_registrationid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cyglffdwsktfeo
--

ALTER SEQUENCE registration_registrationid_seq OWNED BY registration.registrationid;


--
-- Name: sync; Type: TABLE; Schema: public; Owner: cyglffdwsktfeo; Tablespace: 
--

CREATE TABLE sync (
    syncid integer NOT NULL,
    tablename character varying(20),
    lastsync timestamp without time zone
);


ALTER TABLE public.sync OWNER TO cyglffdwsktfeo;

--
-- Name: sync_syncid_seq; Type: SEQUENCE; Schema: public; Owner: cyglffdwsktfeo
--

CREATE SEQUENCE sync_syncid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sync_syncid_seq OWNER TO cyglffdwsktfeo;

--
-- Name: sync_syncid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cyglffdwsktfeo
--

ALTER SEQUENCE sync_syncid_seq OWNED BY sync.syncid;


--
-- Name: user_group; Type: TABLE; Schema: public; Owner: cyglffdwsktfeo; Tablespace: 
--

CREATE TABLE user_group (
    user_groupid integer NOT NULL,
    personid integer NOT NULL,
    groupsid integer NOT NULL,
    contact_only boolean
);


ALTER TABLE public.user_group OWNER TO cyglffdwsktfeo;

--
-- Name: user_group_user_groupid_seq; Type: SEQUENCE; Schema: public; Owner: cyglffdwsktfeo
--

CREATE SEQUENCE user_group_user_groupid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_group_user_groupid_seq OWNER TO cyglffdwsktfeo;

--
-- Name: user_group_user_groupid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cyglffdwsktfeo
--

ALTER SEQUENCE user_group_user_groupid_seq OWNED BY user_group.user_groupid;


--
-- Name: visitor; Type: TABLE; Schema: public; Owner: cyglffdwsktfeo; Tablespace: 
--

CREATE TABLE visitor (
    personid integer NOT NULL,
    username character varying(40),
    password character varying(100),
    access character varying(40),
    role character varying(20),
    last_login timestamp without time zone,
    reset character varying(60),
    reset_expiry timestamp without time zone,
    partner_access integer,
    keyleader_access integer
);


ALTER TABLE public.visitor OWNER TO cyglffdwsktfeo;

--
-- Name: eventid; Type: DEFAULT; Schema: public; Owner: cyglffdwsktfeo
--

ALTER TABLE ONLY event ALTER COLUMN eventid SET DEFAULT nextval('event_eventid_seq'::regclass);


--
-- Name: groupsid; Type: DEFAULT; Schema: public; Owner: cyglffdwsktfeo
--

ALTER TABLE ONLY groups ALTER COLUMN groupsid SET DEFAULT nextval('groups_groupsid_seq'::regclass);


--
-- Name: membershipid; Type: DEFAULT; Schema: public; Owner: cyglffdwsktfeo
--

ALTER TABLE ONLY membership ALTER COLUMN membershipid SET DEFAULT nextval('membership_membershipid_seq'::regclass);


--
-- Name: registrationid; Type: DEFAULT; Schema: public; Owner: cyglffdwsktfeo
--

ALTER TABLE ONLY registration ALTER COLUMN registrationid SET DEFAULT nextval('registration_registrationid_seq'::regclass);


--
-- Name: syncid; Type: DEFAULT; Schema: public; Owner: cyglffdwsktfeo
--

ALTER TABLE ONLY sync ALTER COLUMN syncid SET DEFAULT nextval('sync_syncid_seq'::regclass);


--
-- Name: user_groupid; Type: DEFAULT; Schema: public; Owner: cyglffdwsktfeo
--

ALTER TABLE ONLY user_group ALTER COLUMN user_groupid SET DEFAULT nextval('user_group_user_groupid_seq'::regclass);


--
-- Name: event_pkey; Type: CONSTRAINT; Schema: public; Owner: cyglffdwsktfeo; Tablespace: 
--

ALTER TABLE ONLY event
    ADD CONSTRAINT event_pkey PRIMARY KEY (externalid);


--
-- Name: family_pkey; Type: CONSTRAINT; Schema: public; Owner: cyglffdwsktfeo; Tablespace: 
--

ALTER TABLE ONLY family
    ADD CONSTRAINT family_pkey PRIMARY KEY (familyid);


--
-- Name: person_externalid_index; Type: CONSTRAINT; Schema: public; Owner: cyglffdwsktfeo; Tablespace: 
--

ALTER TABLE ONLY person
    ADD CONSTRAINT person_externalid_index UNIQUE (externalid);


--
-- Name: visitor_pkey; Type: CONSTRAINT; Schema: public; Owner: cyglffdwsktfeo; Tablespace: 
--

ALTER TABLE ONLY visitor
    ADD CONSTRAINT visitor_pkey PRIMARY KEY (personid);


--
-- Name: code_index; Type: INDEX; Schema: public; Owner: cyglffdwsktfeo; Tablespace: 
--

CREATE UNIQUE INDEX code_index ON groups USING btree (code);


--
-- Name: family_number_index; Type: INDEX; Schema: public; Owner: cyglffdwsktfeo; Tablespace: 
--

CREATE INDEX family_number_index ON family USING btree (tagnumber);


--
-- Name: person_family_tag_index; Type: INDEX; Schema: public; Owner: cyglffdwsktfeo; Tablespace: 
--

CREATE INDEX person_family_tag_index ON person USING btree (family_tag);


--
-- Name: username_index; Type: INDEX; Schema: public; Owner: cyglffdwsktfeo; Tablespace: 
--

CREATE UNIQUE INDEX username_index ON visitor USING btree (username);


--
-- PostgreSQL database dump complete
--

