SITIO WEB PARA VOTACIONES CESA

OBJETIVO
Diseñar un sistema de votación descentralizado para las elecciones del Comité Ejecutivo de la
Sociedad de Alumnos (CESA), utilizando Smart Contracts en la blockchain de Algorand, que
asegure un proceso electoral transparente, seguro y confiable para todos los estudiantes.

PROBLEMÁTICA
En el Instituto Tecnológico de Pabellón de Arteaga (ITPA), las elecciones para el Consejo
Ejecutivo de la Sociedad de Alumnos (CESA) enfrentan problemas de falta de transparencia,
manipulación de resultados, baja participación y desconfianza en los procesos de conteo de
votos.
A menudo, el sistema de votación tradicional depende de intermediarios humanos encargados
de registrar, contabilizar y validar los votos, lo que genera un riesgo de errores o manipulación.
Además, que no siempre garantiza anonimato, verificabilidad ni inmutabilidad de los resultados.
En este contexto, la tecnología blockchain, y en particular la red Algorand, ofrece una solución
innovadora que permite crear un sistema de votación seguro, descentralizado y transparente,
donde cada voto quede registrado en una cadena de bloques de manera inmutable y auditable.

REQUERIMIENTO DESCRIPCION PRIORIDAD
RF1 
El sistema deberá permitir registrar a
los estudiantes habilitados para
participar en las elecciones del CESA,
asegurando que cada uno cuente con
una identificación única y que solo los
usuarios autorizados puedan emitir un
voto.
Alta

RF2 
El sistema deberá autenticar al votante
mediante su número de control antes
de permitir el acceso al proceso de
votación, verificando que su dirección
esté registrada en el contrato
inteligente.
Alta

RF3 
El sistema permitirá que cada
estudiante emita su voto por un
candidato registrado. El voto se
registrará como una transacción en la
blockchain de Algorand a través del
Smart Contract, asegurando que sea
anónimo e inmutable.
Muy alta

RF4 
El sistema deberá realizar
automáticamente el conteo de votos
almacenados en el Smart Contract al
cierre del periodo electoral, mostrando
el número total de votos obtenidos por
cada candidato.
Alta

RF5 
El sistema deberá bloquear
automáticamente la posibilidad de
votar una vez alcanzada la fecha o
bloque de finalización establecido en el
Smart Contract.
Media

RF6 
El sistema mostrará los resultados
finales de la votación directamente
desde la blockchain, permitiendo que
cualquier usuario pueda verificar la
información.
Alta

RF7 
El sistema deberá enviar una
notificación al votante mediante correo
o mensaje interno confirmando que su
voto fue recibido y registrado
correctamente en la blockchain.
Baja