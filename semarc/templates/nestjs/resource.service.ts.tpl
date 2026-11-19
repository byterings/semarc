import { ObjectLiteral } from 'typeorm';
import { ApiError, ErrorDetails } from './api-error';
import { decimalValue } from './validation';
import { ResourceRepository } from './resource.repository';

export const DEFAULT_LIMIT = {{default_limit}};
export const MAX_LIMIT = {{max_limit}};

export interface Reference {
  column: string;
  table: string;
  model: string;
  owner?: boolean;
}

export interface Dependent {
  table: string;
  column: string;
  model: string;
}

export interface Page {
  data: Record<string, unknown>[];
  meta: { total: number; limit: number; offset: number };
}

type Data = Record<string, unknown>;

/**
 * Business rules shared by every generated resource: references, uniqueness,
 * ownership and safe deletes. Model services describe their entity and can
 * override beforeWrite().
 */
export abstract class ResourceService<T extends ObjectLiteral> {
  protected abstract readonly name: string;
  protected abstract readonly output: string[];
  protected readonly references: Reference[] = [];
  protected readonly dependents: Dependent[] = [];
  protected readonly unique: string[] = [];
  protected readonly dateTimes: string[] = [];
  protected readonly decimals: string[] = [];
  protected readonly defaults: Data = {};
  protected readonly replaceValues: Data = {};
  protected readonly filters: Record<string, string> = { id: 'INTEGER' };
  protected readonly sortFields: string[] = ['id'];

  protected constructor(protected readonly repository: ResourceRepository<T>) {}

  /** Lists records; query holds equality filters and sort, where holds fixed conditions. */
  async list(limit: number, offset: number, query: Record<string, unknown> = {}, where: Data = {}): Promise<Page> {
    const safeLimit = Math.max(1, Math.min(limit, MAX_LIMIT));
    const safeOffset = Math.max(0, offset);
    const [parsed, orderBy, direction] = this.parseQuery(query);
    const filters = { ...parsed, ...where };
    const records = await this.repository.paginate(safeLimit, safeOffset, filters, orderBy, direction);
    return {
      data: records.map((record) => this.serialize(record)),
      meta: { total: await this.repository.count(filters), limit: safeLimit, offset: safeOffset },
    };
  }

  async listForParent(
    parentTable: string,
    parentName: string,
    column: string,
    parentId: number,
    limit: number,
    offset: number,
    query: Record<string, unknown> = {},
  ): Promise<Page> {
    if (!(await this.repository.rowExists(parentTable, parentId))) {
      throw ApiError.notFound(`${parentName} ${parentId} not found.`);
    }
    return this.list(limit, offset, query, { [column]: parentId });
  }

  async get(id: number): Promise<Data> {
    return this.serialize(await this.find(id));
  }

  async create(input: object, ownerId?: number): Promise<Data> {
    const data = { ...this.defaults, ...this.toStored(defined(input)) };
    this.applyOwner(data, ownerId, true, false);
    await this.checkReferences(data);
    await this.checkUnique(data);
    return this.serialize(await this.repository.create((await this.beforeWrite(data)) as Partial<T>));
  }

  async update(id: number, input: object, partial: boolean, ownerId?: number, manageAll = false): Promise<Data> {
    const record = await this.find(id);
    if (!manageAll) {
      this.checkOwner(record, ownerId);
    }
    const data = this.toStored(defined(input));
    if (!partial) {
      // PUT replaces the record: left-out fields get their DEFAULT, OPTIONAL ones null
      for (const [field, value] of Object.entries(this.replaceValues)) {
        if (!(field in data)) {
          data[field] = value;
        }
      }
    }
    this.applyOwner(data, ownerId, !partial, true);
    if (Object.keys(data).length === 0) {
      return this.serialize(record);
    }
    await this.checkReferences(data);
    await this.checkUnique(data, id);
    return this.serialize(await this.repository.update(record, (await this.beforeWrite(data)) as Partial<T>));
  }

  async delete(id: number, ownerId?: number, manageAll = false): Promise<void> {
    const record = await this.find(id);
    if (!manageAll) {
      this.checkOwner(record, ownerId);
    }
    for (const dependent of this.dependents) {
      if ((await this.repository.countIn(dependent.table, dependent.column, id)) > 0) {
        throw ApiError.conflict(`Cannot delete ${this.name} ${id} while ${dependent.model} records reference it.`);
      }
    }
    await this.repository.delete(record);
  }

  /** Hook for model specific changes before data is stored. */
  protected async beforeWrite(data: Data): Promise<Data> {
    return data;
  }

  protected serialize(record: T): Data {
    const result: Data = {};
    for (const field of this.output) {
      const value = (record as Data)[field];
      result[field] = value instanceof Date ? value.toISOString().replace(/\.\d{3}Z$/, 'Z') : value ?? null;
    }
    return result;
  }

  protected async find(id: number): Promise<T> {
    const record = await this.repository.findById(id);
    if (!record) {
      throw ApiError.notFound(`${this.name} ${id} not found.`);
    }
    return record;
  }

  private parseQuery(query: Record<string, unknown>): [Data, string, 'ASC' | 'DESC'] {
    const errors: ErrorDetails = {};
    const filters: Data = {};
    for (const [field, type] of Object.entries(this.filters)) {
      if (!(field in query)) {
        continue;
      }
      const raw = query[field];
      const value = typeof raw === 'string' ? filterValue(raw, type) : undefined;
      if (value === undefined) {
        errors[field] = [`${field} filter must be ${FILTER_DESCRIPTIONS[type] ?? 'text'}`];
      } else {
        filters[field] = value;
      }
    }

    let orderBy = 'id';
    let direction: 'ASC' | 'DESC' = 'ASC';
    if ('sort' in query) {
      const sort = typeof query.sort === 'string' ? query.sort : '';
      const field = sort.replace(/^-/, '');
      if (!this.sortFields.includes(field)) {
        errors.sort = [`sort must be one of: ${this.sortFields.join(', ')} (prefix with - for descending)`];
      } else {
        orderBy = field;
        direction = sort.startsWith('-') ? 'DESC' : 'ASC';
      }
    }

    if (Object.keys(errors).length > 0) {
      throw ApiError.validation(errors);
    }
    return [filters, orderBy, direction];
  }

  /** ISO 8601 date-time strings are stored as UTC Date values without milliseconds. */
  private toStored(data: Data): Data {
    for (const field of this.decimals) {
      if (data[field] !== null && data[field] !== undefined) {
        data[field] = decimalValue(data[field]);
      }
    }
    for (const field of this.dateTimes) {
      if (typeof data[field] === 'string') {
        const value = new Date(data[field] as string);
        value.setMilliseconds(0);
        data[field] = value;
      }
    }
    return data;
  }

  /** On protected routes, records with an owner column may only be changed by their owner. */
  private checkOwner(record: T, ownerId: number | undefined): void {
    if (ownerId === undefined) {
      return;
    }
    for (const reference of this.references) {
      if (reference.owner && (record as Data)[reference.column] !== ownerId) {
        throw ApiError.forbidden(`Only the owner can modify this ${this.name}.`);
      }
    }
  }

  private applyOwner(data: Data, ownerId: number | undefined, require: boolean, keepExisting: boolean): void {
    for (const reference of this.references) {
      if (!reference.owner) {
        continue;
      }
      if (ownerId !== undefined) {
        if (keepExisting) {
          delete data[reference.column];
        } else {
          data[reference.column] = ownerId;
        }
      } else if (require && (data[reference.column] === undefined || data[reference.column] === null)) {
        throw ApiError.validation({ [reference.column]: [`${reference.column} is required`] });
      }
    }
  }

  private async checkReferences(data: Data): Promise<void> {
    const errors: ErrorDetails = {};
    for (const reference of this.references) {
      const value = data[reference.column];
      if (typeof value === 'number' && !(await this.repository.rowExists(reference.table, value))) {
        errors[reference.column] = [`${reference.column} does not reference an existing ${reference.model}`];
      }
    }
    if (Object.keys(errors).length > 0) {
      throw ApiError.validation(errors);
    }
  }

  private async checkUnique(data: Data, exceptId?: number): Promise<void> {
    const errors: ErrorDetails = {};
    for (const column of this.unique) {
      const value = data[column];
      if (value !== undefined && value !== null && (await this.repository.existsWhere(column, value, exceptId))) {
        errors[column] = [`${column} has already been taken`];
      }
    }
    if (Object.keys(errors).length > 0) {
      throw ApiError.conflict(`${this.name} already exists.`, errors);
    }
  }
}

const FILTER_DESCRIPTIONS: Record<string, string> = {
  INTEGER: 'an integer',
  FLOAT: 'a number',
  DECIMAL: 'a decimal number',
  BOOLEAN: 'true or false',
  DATE: 'a date (YYYY-MM-DD)',
};

function filterValue(raw: string, type: string): unknown {
  switch (type) {
    case 'INTEGER':
      return /^-?\d+$/.test(raw) ? Number(raw) : undefined;
    case 'FLOAT':
      return raw.trim() !== '' && Number.isFinite(Number(raw)) ? Number(raw) : undefined;
    case 'DECIMAL':
      return decimalValue(raw);
    case 'BOOLEAN':
      return ({ true: true, '1': true, false: false, '0': false } as Record<string, boolean>)[raw.toLowerCase()];
    case 'DATE':
      return /^\d{4}-\d{2}-\d{2}$/.test(raw) && !Number.isNaN(Date.parse(raw)) ? raw : undefined;
    default:
      return raw;
  }
}

function defined(input: object): Data {
  return Object.fromEntries(Object.entries(input).filter(([, value]) => value !== undefined));
}

export function pageParams(limit?: string, offset?: string): [number, number] {
  const parse = (value: string | undefined, fallback: number) => (value && /^\d+$/.test(value) ? Number(value) : fallback);
  return [parse(limit, DEFAULT_LIMIT), parse(offset, 0)];
}
