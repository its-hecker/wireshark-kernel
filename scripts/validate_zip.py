import re
import hashlib
import struct
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as archive:
    if archive.testzip() is not None:
        raise SystemExit('ZIP CRC failure')
    names = archive.namelist()
    for name in names:
        if name.startswith('/') or '..' in name.split('/') or '.git' in name.split('/'):
            raise SystemExit(f'Unsafe ZIP member: {name}')
    for name in ('Image.lz4', 'dtb', 'dtbo.img', 'anykernel.sh', 'modules.sha256', 'module-symbols.txt',
                 'META-INF/com/google/android/update-binary', 'tools/ak3-core.sh',
                 'tools/magiskboot', 'tools/busybox', 'tools/module-check'):
        if not archive.read(name):
            raise SystemExit(f'Empty payload: {name}')
    if archive.read('Image.lz4')[:4] not in (b'\x02\x21\x4c\x18', b'\x04\x22\x4d\x18'):
        raise SystemExit('Kernel is not an LZ4 image')
    dtb = archive.read('dtb')
    offset = 0
    while offset < len(dtb):
        magic, size = struct.unpack_from('>II', dtb, offset)
        if magic != 0xD00DFEED or size < 40 or offset + size > len(dtb):
            raise SystemExit('Invalid concatenated DTB')
        offset += size
    dtbo = archive.read('dtbo.img')
    magic, total, header, entry, count, entries, page, version = struct.unpack_from('>8I', dtbo)
    if magic != 0xD7B7AB1E or total != len(dtbo) or header < 32 or entry < 32 or not count or entries + entry * count > total or total > 8388608:
        raise SystemExit('Invalid DTBO table')
    for index in range(count):
        size, offset = struct.unpack_from('>II', dtbo, entries + index * entry)
        if offset + size > total or size < 40 or dtbo[offset:offset + 4] != b'\xd0\x0d\xfe\xed':
            raise SystemExit('Invalid DTBO entry')
    script = archive.read('anykernel.sh').decode()
    for required in ('device.name1=coral', 'IS_SLOT_DEVICE=1', 'split_boot', 'flash_boot', 'flash_generic dtbo'):
        if required not in script:
            raise SystemExit(f'Missing installer requirement: {required}')
    manifest = archive.read('modules.sha256').decode().splitlines()
    if not manifest or not all(re.fullmatch(r'[0-9a-f]{64} [A-Za-z0-9_.-]+\.ko', line) for line in manifest):
        raise SystemExit('Invalid module checksums')
    for line in manifest:
        digest, name = line.split()
        if hashlib.sha256(archive.read(f'module-reference/{name}')).hexdigest() != digest:
            raise SystemExit(f'Invalid module ABI reference: {name}')
    checker = archive.read('tools/module-check')
    if len(checker) < 64 or checker[:6] != b'\x7fELF\x02\x01':
        raise SystemExit('ABI checker is not a little-endian ELF64 executable')
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', checker)
    if header[1] != 2 or header[2] != 183 or header[9] != 56 or header[5] + header[9] * header[10] > len(checker):
        raise SystemExit('ABI checker is not a valid ARM64 executable')
    for index in range(header[10]):
        if struct.unpack_from('<I', checker, header[5] + index * header[9])[0] == 3:
            raise SystemExit('ABI checker requires a dynamic loader')
    for name in ('anykernel.sh', 'META-INF/com/google/android/update-binary', 'tools/module-check'):
        if not (archive.getinfo(name).external_attr >> 16) & 0o111:
            raise SystemExit(f'Installer is not executable: {name}')
print('ZIP structure, device/slot guards, kernel, DTB, DTBO, static ABI checker and module references validated')

