# Optimization Benchmarks

The validation suite measures serialized size, estimated tokens (four characters per token), elapsed optimization time, memory metadata, protected-content retention, and repeatability. These estimates are provider-independent and are not billing measurements.

The canonical Context fixture reduced from 54 to 20 representation bytes and from 13 to 5 estimated tokens. Prompt, artifact, terminal, conversation, Skill, and repository fixtures are covered by deterministic unit tests. On this development host, individual native operations completed below the resolution relevant to interactive invocation; repository AST lookup remains proportional to the number and size of Python files scanned.

Benchmarks favor correctness over maximum compression. Protected content is never removed, and zero reduction is valid when preservation rules require it.
