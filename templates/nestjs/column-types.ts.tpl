import { ColumnType } from 'typeorm';
import { settings } from '../config/settings';

type SemanticType = 'STRING' | 'TEXT' | 'INTEGER' | 'FLOAT' | 'BOOLEAN' | 'DATETIME';

const TYPES: Record<string, Record<SemanticType, ColumnType>> = {
  mysql: { STRING: 'varchar', TEXT: 'text', INTEGER: 'integer', FLOAT: 'double', BOOLEAN: 'boolean', DATETIME: 'datetime' },
  pgsql: { STRING: 'varchar', TEXT: 'text', INTEGER: 'integer', FLOAT: 'double precision', BOOLEAN: 'boolean', DATETIME: 'timestamp' },
  sqlite: { STRING: 'varchar', TEXT: 'text', INTEGER: 'integer', FLOAT: 'real', BOOLEAN: 'boolean', DATETIME: 'datetime' },
};

/** Maps semantic field types to the column type of the configured database. */
export function columnType(type: SemanticType): ColumnType {
  const types = TYPES[settings.dbConnection];
  if (!types) {
    throw new Error(`Unsupported DB_CONNECTION: ${settings.dbConnection} (use mysql, pgsql or sqlite)`);
  }
  return types[type];
}

export function nowUtc(): Date {
  const now = new Date();
  now.setMilliseconds(0);
  return now;
}
