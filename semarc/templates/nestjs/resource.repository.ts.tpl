import { FindOptionsWhere, ObjectLiteral, Repository } from 'typeorm';
import { nowUtc } from '../database/column-types';

type Filters = Record<string, unknown>;

/** Generic TypeORM persistence for one entity. Model repositories extend this class. */
export abstract class ResourceRepository<T extends ObjectLiteral> {
  protected constructor(protected readonly repository: Repository<T>) {}

  paginate(limit: number, offset: number, filters: Filters = {}, orderBy = 'id', direction: 'ASC' | 'DESC' = 'ASC'): Promise<T[]> {
    return this.repository.find({
      where: filters as FindOptionsWhere<T>,
      order: { [orderBy]: direction, id: 'ASC' } as never,
      take: limit,
      skip: offset,
    });
  }

  count(filters: Filters = {}): Promise<number> {
    return this.repository.count({ where: filters as FindOptionsWhere<T> });
  }

  findById(id: number): Promise<T | null> {
    return this.repository.findOne({ where: { id } as unknown as FindOptionsWhere<T> });
  }

  findBy(column: string, value: unknown): Promise<T | null> {
    return this.repository.findOne({ where: { [column]: value } as FindOptionsWhere<T> });
  }

  async existsWhere(column: string, value: unknown, exceptId?: number): Promise<boolean> {
    const query = this.repository
      .createQueryBuilder('record')
      .select('record.id')
      .where(`record.${column} = :value`, { value });
    if (exceptId !== undefined) {
      query.andWhere('record.id <> :exceptId', { exceptId });
    }
    return (await query.getCount()) > 0;
  }

  async rowExists(table: string, id: number): Promise<boolean> {
    const row = await this.repository.manager
      .createQueryBuilder()
      .select('1', 'found')
      .from(table, 'record')
      .where('record.id = :id', { id })
      .getRawOne();
    return row !== undefined;
  }

  async countIn(table: string, column: string, id: number): Promise<number> {
    const row = await this.repository.manager
      .createQueryBuilder()
      .select('COUNT(*)', 'total')
      .from(table, 'record')
      .where(`record.${column} = :id`, { id })
      .getRawOne<{ total: string | number }>();
    return Number(row?.total ?? 0);
  }

  async create(data: Partial<T>): Promise<T> {
    const now = nowUtc();
    const record = this.repository.create({ ...data, created_at: now, updated_at: now } as unknown as T);
    const saved = await this.repository.save(record);
    return (await this.findById(saved.id)) as T;
  }

  async update(record: T, data: Partial<T>): Promise<T> {
    Object.assign(record, data, { updated_at: nowUtc() });
    await this.repository.save(record);
    return (await this.findById(record.id)) as T;
  }

  async delete(record: T): Promise<void> {
    await this.repository.delete(record.id);
  }
}
