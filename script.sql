CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- Ensure pgcrypto extension is available for UUID generation

-- Create batches table with company_count column
CREATE TABLE batches (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,  -- UUID for id
    batch VARCHAR(255) NOT NULL,  -- Batch name or ID
    batch_link TEXT NOT NULL,  -- Link associated with the batch
    year INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Timestamp for last update
    company_count INT DEFAULT 0  -- Count of companies in the batch
);

-- Create industries table
CREATE TABLE industries (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,  -- UUID for id
    industry VARCHAR(255) NOT NULL,  -- Industry name
    industry_link TEXT NOT NULL,  -- Link associated with the industry
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Timestamp for last update
    company_count INT DEFAULT 0  -- Count of companies in the batch
);

-- Create companies table with foreign key referencing batches
create table companies
(
    id                uuid      default gen_random_uuid() not null
        primary key,
    logo              text                                not null,
    company_name      varchar(255)                        not null,
    link              text                                not null,
    location          varchar(255),
    short_description text,
    updated_at        timestamp default CURRENT_TIMESTAMP,
    batch_id          uuid
        references batches,
    tags              text[],
    job_count         varchar(50),
    domain            text,
    description       text,
    team_size         varchar(50),
    primary_partner   text,
    linkedin          text,
    x                 text,
    twitter           text,
    facebook          text,
    github            text,
    crunchbase        text,
    emails            text[],
    worth             boolean default False,
    remarks           text,
    todo               text[]
);

-- Create a join table to associate multiple industries with companies
CREATE TABLE company_industries (
    company_id UUID,  -- Foreign key reference to companies table
    industry_id UUID,  -- Foreign key reference to industries table
    PRIMARY KEY (company_id, industry_id),  -- Composite primary key
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,  -- Foreign key constraint to companies
    FOREIGN KEY (industry_id) REFERENCES industries(id) ON DELETE CASCADE  -- Foreign key constraint to industries
);

-- Create a new table for people associated with companies
CREATE TABLE people (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    company_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    designation VARCHAR(255),
    linkedin TEXT,
    x TEXT,
    twitter TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- Create index for faster lookups
CREATE INDEX idx_people_company_id ON people(company_id);

-- Create a trigger function to update company_count in batches
CREATE OR REPLACE FUNCTION update_company_count()
RETURNS TRIGGER AS $$
BEGIN
    -- When a new company is inserted, increment the count for the corresponding batch
    IF TG_OP = 'INSERT' THEN
        UPDATE batches
        SET company_count = company_count + 1
        WHERE id = NEW.batch_id;
    -- When a company is deleted, decrement the count for the corresponding batch
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE batches
        SET company_count = company_count - 1
        WHERE id = OLD.batch_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create a trigger on the companies table to update company_count in batches
CREATE TRIGGER company_count_trigger
AFTER INSERT OR DELETE ON companies
FOR EACH ROW EXECUTE FUNCTION update_company_count();

-- Create a trigger function to update company_count in industries
CREATE OR REPLACE FUNCTION update_industry_company_count()
RETURNS TRIGGER AS $$
BEGIN
    -- When a new company-industry association is inserted
    IF TG_OP = 'INSERT' THEN
        UPDATE industries
        SET company_count = company_count + 1
        WHERE id = NEW.industry_id;
    -- When a company-industry association is deleted
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE industries
        SET company_count = company_count - 1
        WHERE id = OLD.industry_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create a trigger on the company_industries table to update company_count in industries
CREATE TRIGGER industry_company_count_trigger
AFTER INSERT OR DELETE ON company_industries
FOR EACH ROW EXECUTE FUNCTION update_industry_company_count();
