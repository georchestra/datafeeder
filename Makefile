install:
	./mvnw clean install -DskipTests

test:
	./mvnw clean verify

its:
	./mvnw clean verify  -DskipITs=false -DskipTests

release:
	./mvnw clean release:prepare -Darguments="-DskipTests -DskipITs"

deb:
	mvn package deb:package -PdebianPackage -DskipTests ${DEPLOY_OPTS}
