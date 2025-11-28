import asyncio
import logging
from io import BytesIO

from fastapi import UploadFile
from miniopy_async import Minio, S3Error
from miniopy_async.commonconfig import CopySource

from config import settings

MINIO = settings.yaml_config.get("minio")

class AsyncSimpleMinio:
    # __init__ 是同步的，适合用来创建客户端实例
    def __init__(self):
        # 客户端实例的创建本身是同步的，它只是配置参数
        self.conn = Minio(
            MINIO["host"],
            access_key=MINIO["username"],
            secret_key=MINIO["password"],
            secure=False
        )
    async def put_by_user_file(self, bucket: str, fnm: str, file: UploadFile):
        """
        FastAPI上传文件
        """
        for _ in range(3):
            try:
                # 3. 所有客户端IO调用前加上 await
                if not await self.conn.bucket_exists(bucket):
                    await self.conn.make_bucket(bucket)
                file_size = file.size
                # 注意：miniopy-async 的 put_object 接受一个可读对象
                r = await self.conn.put_object(
                    bucket, fnm, data=file.file, length=file_size
                )
                return r
            except Exception:
                logging.exception(f"Fail to put {bucket}/{fnm}:")
                # 4. time.sleep 需要换成 asyncio.sleep
                await asyncio.sleep(1)
        return None

    async def _put(self, bucket: str, fnm: str, binary: bytes):
        for _ in range(3):
            try:
                # 3. 所有客户端IO调用前加上 await
                if not await self.conn.bucket_exists(bucket):
                    await self.conn.make_bucket(bucket)

                # 注意：miniopy-async 的 put_object 接受一个可读对象
                r = await self.conn.put_object(
                    bucket, fnm, BytesIO(binary), length=len(binary)
                )
                return r
            except Exception:
                logging.exception(f"Fail to put {bucket}/{fnm}:")
                # 4. time.sleep 需要换成 asyncio.sleep
                await asyncio.sleep(1)
        return None

    async def rm(self, bucket: str, fnm: str):
        try:
            await self.conn.remove_object(bucket, fnm)
        except Exception:
            logging.exception(f"Fail to remove {bucket}/{fnm}:")

    async def get(self, bucket: str, filename: str):
        for _ in range(3):
            try:

                response = await self.conn.get_object(bucket, filename)
                return await response.read()
            except Exception:
                logging.exception(f"Fail to get {bucket}/{filename}")
                await asyncio.sleep(1)
        return None

    async def obj_exist(self, bucket: str, filename: str):
        try:
            if not await self.conn.bucket_exists(bucket):
                return False
            # stat_object 在对象不存在时会抛出异常，所以直接 try/except 即可
            await self.conn.stat_object(bucket, filename)
            return True
        except S3Error as e:
            if e.code in ["NoSuchKey", "NoSuchBucket", "ResourceNotFound"]:
                return False
            # 其他S3Error需要记录
            logging.exception(f"obj_exist {bucket}/{filename} got S3Error: {e}")
            return False
        except Exception:
            logging.exception(f"obj_exist {bucket}/{filename} got unexpected exception")
            return False

    async def get_presigned_url(self, bucket: str, fnm: str, expires: int):
        for _ in range(10):
            try:
                return await self.conn.get_presigned_url("GET", bucket, fnm, expires=expires)
            except Exception:
                logging.exception(f"Fail to get_presigned {bucket}/{fnm}:")
                await asyncio.sleep(1)
        return None

    async def remove_bucket(self, bucket: str):
        try:
            if await self.conn.bucket_exists(bucket):
                # 5. list_objects 返回异步迭代器，需要用 async for
                objects_to_delete = self.conn.list_objects(bucket, recursive=True)
                async for obj in objects_to_delete:
                    await self.conn.remove_object(bucket, obj.object_name)
                await self.conn.remove_bucket(bucket)
        except Exception:
            logging.exception(f"Fail to remove bucket {bucket}")

    async def init_directory(self, bucket: str, fnm: str):
        for _ in range(3):
            try:
                if not await self.conn.bucket_exists(bucket):
                    await self.conn.make_bucket(bucket)

                r = await self.conn.put_object(bucket, fnm, BytesIO(b''), length=0)
                return True
            except Exception:
                logging.exception(f"Fail to init directory {bucket}/{fnm}:")
                await asyncio.sleep(1)
        return False

    async def initCreateBucket(self, bucket_name: str):
        found = await self.conn.bucket_exists(bucket_name)
        if not found:
            try:
                await self.conn.make_bucket(bucket_name)
                policy = f"""{{
                        "Version": "2012-10-17",
                        "Statement": [
                            {{
                                "Sid": "PublicRead",
                                "Effect": "Allow",
                                "Principal": "*",
                                "Action": ["s3:GetObject"],
                                "Resource": ["arn:aws:s3:::{bucket_name}/*"]
                            }}
                        ]
                    }}"""
                await self.conn.set_bucket_policy(bucket_name, policy)
                logging.info(f"桶 '{bucket_name}' 创建成功.")
                return True
            except S3Error as err:
                logging.error(f"Error occurred: {err}")
        else:
            logging.info(f"桶 '{bucket_name}' 存在.")
        return False

    async def copy_file_in_bucket(self, source_bucket: str, source_file_path: str, target_bucket: str,
                                  target_path: str):
        copy_source = CopySource(source_bucket, source_file_path)
        try:
            await self.conn.copy_object(
                bucket_name=target_bucket,
                object_name=target_path,
                source=copy_source
            )
            logging.info(f"文件从桶‘{source_bucket}’的‘{source_file_path}’ 复制到桶‘{target_bucket}’的‘{target_path}’")
        except S3Error as e:
            logging.error(f"复制失败: {e}")


# 实例化方式不变
STORAGE_IMPL = AsyncSimpleMinio()
