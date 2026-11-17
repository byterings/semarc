import { ObjectLiteral } from 'typeorm';
import { ApiError, ErrorDetails } from './api-error';
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

  protected constructor(protected readonly repository: ResourceRepository<T>) {}

  async list(limit: number, offset: number, filters: Data = {}): Promise<Page> {
    const safeLimit = Math.max(1, Math.min(limit, MAX_LIMIT));
    const safeOffset = Math.max(0, offset);
    const records = await this.repository.paginate(safeLimit, safeOffset, filters);
    return {
      data: records.map((record) => this.serialize(record)),
      meta: { total: await this.repository.count(filters), limit: safeLimit, offset: safeOffset },
    };
  }

  async listForParent(parentTable: string, parentName: string, column: string, parentId: number, limit: number, offset: number): Promise<Page> {
    if (!(await this.repository.rowExists(parentTable, parentId))) {
      throw ApiError.notFound(`${parentName} ${parentId} not found.`);
    }
    return this.list(limit, offset, { [column]: parentId });
  }

  async get(id: number): Promise<Data> {
    return this.serialize(await this.find(id));
  }

  async create(input: object, ownerId?: number): Promise<Data> {
    const data = this.toStored(defined(input));
    this.applyOwner(data, ownerId, true, false);
    await this.checkReferences(data);
    await this.checkUnique(data);
    return this.serialize(await this.repository.create((await this.beforeWrite(data)) as Partial<T>));
  }

  async update(id: number, input: object, partial: boolean, ownerId?: number): Promise<Data> {
    const record = await this.find(id);
    this.checkOwner(record, ownerId);
    const data = this.toStored(defined(input));
    this.applyOwner(data, ownerId, !partial, true);
    if (Object.keys(data).length === 0) {
      return this.serialize(record);
    }
    await this.checkReferences(data);
    await this.checkUnique(data, id);
    return this.serialize(await this.repository.update(record, (await this.beforeWrite(data)) as Partial<T>));
  }

  async delete(id: number, ownerId?: number): Promise<void> {
    const record = await this.find(id);
    this.checkOwner(record, ownerId);
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

  /** ISO 8601 date-time strings are stored as UTC Date values without milliseconds. */
  private toStored(data: Data): Data {
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

function defined(input: object): Data {
  return Object.fromEntries(Object.entries(input).filter(([, value]) => value !== undefined));
}

export function pageParams(limit?: string, offset?: string): [number, number] {
  const parse = (value: string | undefined, fallback: number) => (value && /^\d+$/.test(value) ? Number(value) : fallback);
  return [parse(limit, DEFAULT_LIMIT), parse(offset, 0)];
}
