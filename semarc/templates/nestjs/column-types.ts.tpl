import { ColumnType } from 'typeorm';
import { settings } from '../config/settings';

type SemanticType = 'STRING' | 'TEXT' | 'INTEGER' | 'FLOAT' | 'DECIMAL' | 'BOOLEAN' | 'DATE' | 'DATETIME';

const TYPES: Record<string, Record<SemanticType, ColumnType>> = {
  mysql: { STRING: 'varchar', TEXT: 'text', INTEGER: 'integer', FLOAT: 'double', DECIMAL: 'decimal', BOOLEAN: 'boolean', DATE: 'date', DATETIME: 'datetime' },
  pgsql: { STRING: 'varchar', TEXT: 'text', INTEGER: 'integer', FLOAT: 'double precision', DECIMAL: 'numeric', BOOLEAN: 'boolean', DATE: 'date', DATETIME: 'timestamp' },
  sqlite: { STRING: 'varchar', TEXT: 'text', INTEGER: 'integer', FLOAT: 'real', DECIMAL: 'decimal', BOOLEAN: 'boolean', DATE: 'date', DATETIME: 'datetime' },
};

/** Maps semantic field types to the column type of the configured database. */
export function columnType(type: SemanticType): ColumnType {
  const types = TYPES[settings.dbConnection];
  if (!types) {
    throw new Error(`Unsupported DB_CONNECTION: ${settings.dbConnection} (use mysql, pgsql or sqlite)`);
  }
  return types[type];
}

/** DECIMAL columns are read as strings with exactly two decimals on every database. */
export const decimalText = {
  to: (value: string | null | undefined) => value,
  from: (value: string | number | null) => (value === null || value === undefined ? value : Number(value).toFixed(2)),
};

export function nowUtc(): Date {
  const now = new Date();
  now.setMilliseconds(0);
  return now;
}
