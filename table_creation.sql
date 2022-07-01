CREATE TYPE sensor_source AS ENUM ('id 0', 'id 1', 'aggregate sensor');
CREATE TYPE concentration_units_types AS ENUM ('U/mL', 'g/100mL', '%wt');
CREATE TYPE log_types AS ENUM ('data log', 'error log');

CREATE TABLE patient (
  id SERIAL,
  mr_number TEXT,
  PRIMARY KEY(id)
);

CREATE TABLE session (
  id SERIAL,
  weight_kg FLOAT,
  glucose_units FLOAT,
  control_range_mg_dl TEXT,
  initial_glucose_mg_dl FLOAT,
  PRIMARY KEY(id),
  patient_id INTEGER REFERENCES patient(id)
);

CREATE TABLE log (
  id SERIAL,
  original_log_name TEXT,
  log_type log_types,
  PRIMARY KEY(id),
  session_id INTEGER REFERENCES session(id)
);

CREATE TABLE glucose (
  id SERIAL,
  timestamp TIMESTAMP,
  relative_timestamp FLOAT,
  source sensor_source,
  value_mg_dl FLOAT,
  PRIMARY KEY(id),
  patient_id INTEGER REFERENCES patient(id),
  log_source INTEGER REFERENCES log(id)
);

CREATE TABLE pump_rate (
  id SERIAL,
  timestamp TIMESTAMP,
  relative_timestamp FLOAT,
  rate_ml_hr FLOAT,
  substance TEXT,
  concentration FLOAT,
  concentration_units concentration_units_types,
  PRIMARY KEY(id),
  patient_id INTEGER REFERENCES patient(id),
  log_source INTEGER REFERENCES log(id)
);

