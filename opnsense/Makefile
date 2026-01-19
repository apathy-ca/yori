PLUGIN_NAME=		yori
PLUGIN_VERSION=		0.1.0
PLUGIN_COMMENT=		Zero-trust LLM governance for home networks
PLUGIN_DEPENDS=		python39 py39-fastapi py39-uvicorn py39-httpx py39-pydantic py39-yaml
PLUGIN_MAINTAINER=	yori@example.com
PLUGIN_WWW=		https://github.com/yourusername/yori

# Plugin categories (shown in OPNsense package manager)
PLUGIN_CATEGORIES=	security

# Include OPNsense plugin build framework
# Note: This would normally be: .include "../../Mk/plugins.mk"
# For standalone development, we'll use a simplified build process

PREFIX?=		/usr/local
CURDIR:=		$(shell pwd)
STAGEDIR?=		$(CURDIR)/work/stage
PACKAGE_NAME=		os-${PLUGIN_NAME}-${PLUGIN_VERSION}.txz

.PHONY: all clean install package

all: package

# Create staging directory with proper structure
stage:
	@echo "Staging plugin files..."
	@mkdir -p ${STAGEDIR}${PREFIX}
	@cp -r src/* ${STAGEDIR}${PREFIX}/
	@mkdir -p ${STAGEDIR}${PREFIX}/opnsense/version/
	@echo "${PLUGIN_NAME} ${PLUGIN_VERSION}" > ${STAGEDIR}${PREFIX}/opnsense/version/${PLUGIN_NAME}

# Build the package
package: stage
	@echo "Building package ${PACKAGE_NAME}..."
	@mkdir -p $(CURDIR)/work
	@cd ${STAGEDIR} && \
		find . -type f -o -type l | sed 's|^\./||' > $(CURDIR)/work/plist && \
		tar -czf $(CURDIR)/${PACKAGE_NAME} -T $(CURDIR)/work/plist
	@echo "Package created: ${PACKAGE_NAME}"
	@ls -lh ${PACKAGE_NAME}

# Install to local system (for testing)
install: stage
	@echo "Installing to ${PREFIX}..."
	@cp -r ${STAGEDIR}${PREFIX}/* ${PREFIX}/
	@echo "Installed successfully"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@rm -rf work/
	@rm -f *.txz
	@echo "Clean complete"

# Show package contents
list:
	@echo "Package contents:"
	@tar -tzf ${PACKAGE_NAME} 2>/dev/null || echo "Package not built yet. Run 'make package' first."

# Development helpers
dev-install: all
	@echo "Installing package for development testing..."
	@pkg add -f ${PACKAGE_NAME}

dev-uninstall:
	@echo "Removing development package..."
	@pkg delete -y os-${PLUGIN_NAME} || true
