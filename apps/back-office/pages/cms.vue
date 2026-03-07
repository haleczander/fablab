<template>
  <main class="bo-wrap cms-studio">
    <header class="hero">
      <div>
        <h1>CMS Studio</h1>
        <p>Edition dans l'apercu, reglages a droite.</p>
      </div>
      <div class="hero-actions">
        <button class="ghost" :disabled="busy" @click="addSection">Nouvelle section</button>
        <button class="ghost" :disabled="busy" @click="reload">Recharger</button>
        <button class="ghost" :disabled="busy" @click="saveDraft">Sauvegarder</button>
        <button :disabled="busy" @click="publish">Publier</button>
      </div>
    </header>

    <section class="meta card">
      <p><strong>Version publiee:</strong> {{ bundle?.published_version ?? "-" }}</p>
      <p><strong>Derniere mise a jour:</strong> {{ fmtDate(bundle?.updated_at) }}</p>
      <p><strong>Derniere publication:</strong> {{ fmtDate(bundle?.published_at) }}</p>
      <p class="msg" :class="msgType">{{ msg }}</p>
    </section>

    <section class="studio-layout">
      <article class="card studio-canvas">
        <div class="studio-toolbar">
          <div class="tabs">
            <span v-for="item in navPreviewItems" :key="item.key">{{ item.label }}</span>
          </div>
        </div>

        <div class="block-palette">
          <button class="palette-chip palette-chip-section" draggable="true" @dragstart="onSectionPaletteDragStart">
            Section
          </button>
          <button v-for="type in blockPalette" :key="type.kind" class="palette-chip" draggable="true" @dragstart="onPaletteDragStart(type.kind)">
            {{ type.label }}
          </button>
        </div>

        <div class="canvas-stack" @dragover.prevent @drop="onCanvasStackDrop">
          <section v-if="rootSection" class="canvas-root">
            <div class="canvas-root-head">
              <span>Racine</span>
            </div>
            <div class="canvas-grid canvas-grid-root" :style="sectionStyle(rootSection)" @dragover.prevent="onParentHover(rootSection.id, null, rootSection.layout, $event)" @drop="onParentDrop(rootSection.id, null, rootSection.layout, $event)">

              <template v-for="(block, blockIndex) in rootSection.blocks" :key="block.id">
                <div class="canvas-drop-slot" :class="{ active: isDropTarget(rootSection.id, null, blockIndex) }" @dragover.prevent="setDropTarget(rootSection.id, null, blockIndex)" @drop="onBlockInsertDrop(rootSection.id, null, blockIndex)" />
                <article
                  class="canvas-block"
                  :class="{ selected: selection?.type === 'block' && selection.blockId === block.id }"
                  :style="blockStyle(rootSection, block)"
                  draggable="true"
                  @click.stop="selectBlock(rootSection.id, block.id)"
                  @dragstart="onBlockDragStart(rootSection.id, block.id)"
                >
                  <template v-if="block.kind === 'machines_feed'">
                    <div class="canvas-block-head">
                      <input class="canvas-block-title" :value="block.title" :placeholder="titlePlaceholder(block.kind)" @input="onBlockTitleInput(rootSection.id, block.id, $event)" @click.stop />
                    </div>
                    <div class="block-preview-machine">
                      <div class="mini-kpi"><span>Etat des machines</span><span>WS live</span></div>
                      <div class="mini-bars"><i /><i /><i /></div>
                    </div>
                  </template>

                  <template v-else-if="block.kind === 'image'">
                    <input class="canvas-block-title" :value="block.title" :placeholder="titlePlaceholder(block.kind)" @input="onBlockTitleInput(rootSection.id, block.id, $event)" @click.stop />
                    <div class="block-preview-image" :class="{ empty: !block.image_url }">
                      <img v-if="block.image_url" :src="block.image_url" :alt="block.title" />
                      <span v-else>Image non renseignee</span>
                    </div>
                  </template>

                  <template v-else-if="block.kind === 'banner'">
                    <div class="block-preview-banner" :style="bannerStyle(block)">
                      <input class="canvas-block-title banner-title" :value="block.title" :placeholder="titlePlaceholder(block.kind)" @input="onBlockTitleInput(rootSection.id, block.id, $event)" @click.stop />
                      <textarea class="canvas-block-body banner-body" :value="block.body || ''" placeholder="Texte de banniere" @input="onBlockBodyInput(rootSection.id, block.id, $event)" @click.stop />
                    </div>
                  </template>

                  <template v-else-if="block.kind === 'container'">
                    <div class="canvas-container-drop" :style="containerStyle(block)" @dragover.prevent="onParentHover(rootSection.id, block.id, block.container_layout, $event)" @drop.stop="onParentDrop(rootSection.id, block.id, block.container_layout, $event)">
                      <div v-if="block.children.length === 0" class="canvas-empty-drop" @dragover.prevent @drop.stop="onBlockInsertDrop(rootSection.id, block.id, 0)">
                        Deposer des blocs dans le container
                      </div>
                      <template v-for="(child, childIndex) in block.children" :key="child.id">
                        <div class="canvas-drop-slot" :class="{ active: isDropTarget(rootSection.id, block.id, childIndex) }" @dragover.prevent="setDropTarget(rootSection.id, block.id, childIndex)" @drop.stop="onBlockInsertDrop(rootSection.id, block.id, childIndex)" />
                        <article
                          class="canvas-block canvas-block-child"
                          :class="{ selected: selection?.type === 'block' && selection.blockId === child.id }"
                          :style="blockStyle(rootSection, child)"
                          draggable="true"
                          @click.stop="selectBlock(rootSection.id, child.id)"
                          @dragstart="onBlockDragStart(rootSection.id, child.id)"
                        >
                          <template v-if="child.kind === 'machines_feed'">
                            <div class="canvas-block-head">
                              <input class="canvas-block-title" :value="child.title" :placeholder="titlePlaceholder(child.kind)" @input="onBlockTitleInput(rootSection.id, child.id, $event)" @click.stop />
                            </div>
                            <div class="block-preview-machine">
                              <div class="mini-kpi"><span>Etat des machines</span><span>WS live</span></div>
                              <div class="mini-bars"><i /><i /><i /></div>
                            </div>
                          </template>
                          <template v-else-if="child.kind === 'image'">
                            <input class="canvas-block-title" :value="child.title" :placeholder="titlePlaceholder(child.kind)" @input="onBlockTitleInput(rootSection.id, child.id, $event)" @click.stop />
                            <div class="block-preview-image" :class="{ empty: !child.image_url }">
                              <img v-if="child.image_url" :src="child.image_url" :alt="child.title" />
                              <span v-else>Image non renseignee</span>
                            </div>
                          </template>
                          <template v-else-if="child.kind === 'banner'">
                            <div class="block-preview-banner" :style="bannerStyle(child)">
                              <input class="canvas-block-title banner-title" :value="child.title" :placeholder="titlePlaceholder(child.kind)" @input="onBlockTitleInput(rootSection.id, child.id, $event)" @click.stop />
                              <textarea class="canvas-block-body banner-body" :value="child.body || ''" placeholder="Texte de banniere" @input="onBlockBodyInput(rootSection.id, child.id, $event)" @click.stop />
                            </div>
                          </template>
                          <template v-else-if="child.kind === 'container'">
                            <div class="canvas-container-drop" :style="containerStyle(child)" @dragover.prevent="onParentHover(rootSection.id, child.id, child.container_layout, $event)" @drop.stop="onParentDrop(rootSection.id, child.id, child.container_layout, $event)">
                              <div v-if="child.children.length === 0" class="canvas-empty-drop" @dragover.prevent @drop.stop="onBlockInsertDrop(rootSection.id, child.id, 0)">Deposer des blocs dans le container</div>
                              <template v-for="(grandchild, grandchildIndex) in child.children" :key="grandchild.id">
                                <div class="canvas-drop-slot" :class="{ active: isDropTarget(rootSection.id, child.id, grandchildIndex) }" @dragover.prevent="setDropTarget(rootSection.id, child.id, grandchildIndex)" @drop.stop="onBlockInsertDrop(rootSection.id, child.id, grandchildIndex)" />
                                <article class="canvas-block canvas-block-child" :class="{ selected: selection?.type === 'block' && selection.blockId === grandchild.id }" :style="blockStyle(rootSection, grandchild)" draggable="true" @click.stop="selectBlock(rootSection.id, grandchild.id)" @dragstart="onBlockDragStart(rootSection.id, grandchild.id)">
                                  <input class="canvas-block-title" :value="grandchild.title" :placeholder="titlePlaceholder(grandchild.kind)" @input="onBlockTitleInput(rootSection.id, grandchild.id, $event)" @click.stop />
                                </article>
                              </template>
                              <div v-if="child.children.length > 0" class="canvas-drop-slot tail" :class="{ active: isDropTarget(rootSection.id, child.id, child.children.length) }" @dragover.prevent="setDropTarget(rootSection.id, child.id, child.children.length)" @drop.stop="onBlockInsertDrop(rootSection.id, child.id, child.children.length)" />
                            </div>
                          </template>
                          <template v-else>
                            <input class="canvas-block-title" :value="child.title" :placeholder="titlePlaceholder(child.kind)" @input="onBlockTitleInput(rootSection.id, child.id, $event)" @click.stop />
                            <textarea class="canvas-block-body" :value="child.body || ''" :placeholder="bodyPlaceholder(child.kind)" @input="onBlockBodyInput(rootSection.id, child.id, $event)" @click.stop />
                            <span v-if="child.link_to_section_id" class="block-link-badge">Lien vers une autre section</span>
                          </template>
                        </article>
                      </template>
                      <div class="canvas-drop-slot tail" :class="{ active: isDropTarget(rootSection.id, block.id, block.children.length) }" @dragover.prevent="setDropTarget(rootSection.id, block.id, block.children.length)" @drop.stop="onBlockInsertDrop(rootSection.id, block.id, block.children.length)" />
                    </div>
                  </template>

                  <template v-else>
                    <input class="canvas-block-title" :value="block.title" :placeholder="titlePlaceholder(block.kind)" @input="onBlockTitleInput(rootSection.id, block.id, $event)" @click.stop />
                    <textarea class="canvas-block-body" :value="block.body || ''" :placeholder="bodyPlaceholder(block.kind)" @input="onBlockBodyInput(rootSection.id, block.id, $event)" @click.stop />
                    <span v-if="block.link_to_section_id" class="block-link-badge">Lien vers une autre section</span>
                  </template>
                </article>
              </template>

              <div v-if="rootSection.blocks.length > 0" class="canvas-drop-slot tail" :class="{ active: isDropTarget(rootSection.id, null, rootSection.blocks.length) }" @dragover.prevent="setDropTarget(rootSection.id, null, rootSection.blocks.length)" @drop="onBlockInsertDrop(rootSection.id, null, rootSection.blocks.length)" />
            </div>
            <div v-if="visibleSections.length > 0" class="canvas-root-sections">
              <article
                v-for="section in visibleSections"
                :key="section.id"
                class="canvas-section"
                :class="{ selected: selection?.type === 'section' && selection.sectionId === section.id }"
                :style="sectionCardStyle(section)"
                draggable="true"
                @click="selectSection(section.id)"
                @dragstart="onSectionDragStart(draft.sections.findIndex((item) => item.id === section.id))"
                @dragover.prevent
                @drop="onSectionDrop(draft.sections.findIndex((item) => item.id === section.id))"
              >
                <header v-if="hasVisibleSectionHeader(section)" class="canvas-section-head">
                  <div class="canvas-title-wrap">
                    <input class="canvas-section-title" :value="section.title" @input="onSectionTitleInput(section.id, $event)" @click.stop />
                    <p class="canvas-kicker">{{ section.nav_label || section.title }}</p>
                  </div>
                  <span>{{ layoutLabel(section.layout) }}</span>
                </header>

                <div class="canvas-grid" :style="sectionStyle(section)" @dragover.prevent="onParentHover(section.id, null, section.layout, $event)" @drop="onParentDrop(section.id, null, section.layout, $event)">
                  <div v-if="section.blocks.length === 0" class="canvas-empty-drop" @dragover.prevent @drop="onEmptySectionDrop(section.id)">
                    Deposer un bloc ici
                  </div>

                  <template v-for="(block, blockIndex) in section.blocks" :key="block.id">
                    <div class="canvas-drop-slot" :class="{ active: isDropTarget(section.id, null, blockIndex) }" @dragover.prevent="setDropTarget(section.id, null, blockIndex)" @drop="onBlockInsertDrop(section.id, null, blockIndex)" />
                    <article
                      class="canvas-block"
                      :class="{ selected: selection?.type === 'block' && selection.blockId === block.id }"
                      :style="blockStyle(section, block)"
                      draggable="true"
                      @click.stop="selectBlock(section.id, block.id)"
                      @dragstart="onBlockDragStart(section.id, block.id)"
                    >
                      <template v-if="block.kind === 'machines_feed'">
                        <div class="canvas-block-head">
                          <input class="canvas-block-title" :value="block.title" :placeholder="titlePlaceholder(block.kind)" @input="onBlockTitleInput(section.id, block.id, $event)" @click.stop />
                        </div>
                        <div class="block-preview-machine">
                          <div class="mini-kpi"><span>Etat des machines</span><span>WS live</span></div>
                          <div class="mini-bars"><i /><i /><i /></div>
                        </div>
                      </template>

                      <template v-else-if="block.kind === 'image'">
                        <input class="canvas-block-title" :value="block.title" :placeholder="titlePlaceholder(block.kind)" @input="onBlockTitleInput(section.id, block.id, $event)" @click.stop />
                        <div class="block-preview-image" :class="{ empty: !block.image_url }">
                          <img v-if="block.image_url" :src="block.image_url" :alt="block.title" />
                          <span v-else>Image non renseignee</span>
                        </div>
                      </template>

                      <template v-else-if="block.kind === 'banner'">
                        <div class="block-preview-banner" :style="bannerStyle(block)">
                          <input class="canvas-block-title banner-title" :value="block.title" :placeholder="titlePlaceholder(block.kind)" @input="onBlockTitleInput(section.id, block.id, $event)" @click.stop />
                          <textarea class="canvas-block-body banner-body" :value="block.body || ''" placeholder="Texte de banniere" @input="onBlockBodyInput(section.id, block.id, $event)" @click.stop />
                        </div>
                      </template>

                      <template v-else-if="block.kind === 'container'">
                        <div class="canvas-container-drop" :style="containerStyle(block)" @dragover.prevent="onParentHover(section.id, block.id, block.container_layout, $event)" @drop.stop="onParentDrop(section.id, block.id, block.container_layout, $event)">
                          <div v-if="block.children.length === 0" class="canvas-empty-drop" @dragover.prevent @drop.stop="onBlockInsertDrop(section.id, block.id, 0)">
                            Deposer des blocs dans le container
                          </div>
                          <template v-for="(child, childIndex) in block.children" :key="child.id">
                            <div class="canvas-drop-slot" :class="{ active: isDropTarget(section.id, block.id, childIndex) }" @dragover.prevent="setDropTarget(section.id, block.id, childIndex)" @drop.stop="onBlockInsertDrop(section.id, block.id, childIndex)" />
                            <article
                              class="canvas-block canvas-block-child"
                              :class="{ selected: selection?.type === 'block' && selection.blockId === child.id }"
                              :style="blockStyle(section, child)"
                              draggable="true"
                              @click.stop="selectBlock(section.id, child.id)"
                              @dragstart="onBlockDragStart(section.id, child.id)"
                            >
                              <template v-if="child.kind === 'machines_feed'">
                                <div class="canvas-block-head">
                                  <input class="canvas-block-title" :value="child.title" :placeholder="titlePlaceholder(child.kind)" @input="onBlockTitleInput(section.id, child.id, $event)" @click.stop />
                                </div>
                                <div class="block-preview-machine">
                                  <div class="mini-kpi"><span>Etat des machines</span><span>WS live</span></div>
                                  <div class="mini-bars"><i /><i /><i /></div>
                                </div>
                              </template>

                              <template v-else-if="child.kind === 'image'">
                                <input class="canvas-block-title" :value="child.title" :placeholder="titlePlaceholder(child.kind)" @input="onBlockTitleInput(section.id, child.id, $event)" @click.stop />
                                <div class="block-preview-image" :class="{ empty: !child.image_url }">
                                  <img v-if="child.image_url" :src="child.image_url" :alt="child.title" />
                                  <span v-else>Image non renseignee</span>
                                </div>
                              </template>

                              <template v-else-if="child.kind === 'banner'">
                                <div class="block-preview-banner" :style="bannerStyle(child)">
                                  <input class="canvas-block-title banner-title" :value="child.title" :placeholder="titlePlaceholder(child.kind)" @input="onBlockTitleInput(section.id, child.id, $event)" @click.stop />
                                  <textarea class="canvas-block-body banner-body" :value="child.body || ''" placeholder="Texte de banniere" @input="onBlockBodyInput(section.id, child.id, $event)" @click.stop />
                                </div>
                              </template>

                              <template v-else-if="child.kind === 'container'">
                                <div class="canvas-container-drop" :style="containerStyle(child)" @dragover.prevent="onParentHover(section.id, child.id, child.container_layout, $event)" @drop.stop="onParentDrop(section.id, child.id, child.container_layout, $event)">
                                  <div v-if="child.children.length === 0" class="canvas-empty-drop" @dragover.prevent @drop.stop="onBlockInsertDrop(section.id, child.id, 0)">Deposer des blocs dans le container</div>
                                  <template v-for="(grandchild, grandchildIndex) in child.children" :key="grandchild.id">
                                    <div class="canvas-drop-slot" :class="{ active: isDropTarget(section.id, child.id, grandchildIndex) }" @dragover.prevent="setDropTarget(section.id, child.id, grandchildIndex)" @drop.stop="onBlockInsertDrop(section.id, child.id, grandchildIndex)" />
                                    <article class="canvas-block canvas-block-child" :class="{ selected: selection?.type === 'block' && selection.blockId === grandchild.id }" :style="blockStyle(section, grandchild)" draggable="true" @click.stop="selectBlock(section.id, grandchild.id)" @dragstart="onBlockDragStart(section.id, grandchild.id)">
                                      <input class="canvas-block-title" :value="grandchild.title" :placeholder="titlePlaceholder(grandchild.kind)" @input="onBlockTitleInput(section.id, grandchild.id, $event)" @click.stop />
                                    </article>
                                  </template>
                                  <div v-if="child.children.length > 0" class="canvas-drop-slot tail" :class="{ active: isDropTarget(section.id, child.id, child.children.length) }" @dragover.prevent="setDropTarget(section.id, child.id, child.children.length)" @drop.stop="onBlockInsertDrop(section.id, child.id, child.children.length)" />
                                </div>
                              </template>

                              <template v-else>
                                <input class="canvas-block-title" :value="child.title" :placeholder="titlePlaceholder(child.kind)" @input="onBlockTitleInput(section.id, child.id, $event)" @click.stop />
                                <textarea class="canvas-block-body" :value="child.body || ''" :placeholder="bodyPlaceholder(child.kind)" @input="onBlockBodyInput(section.id, child.id, $event)" @click.stop />
                                <span v-if="child.link_to_section_id" class="block-link-badge">Lien vers une autre section</span>
                              </template>
                            </article>
                          </template>
                          <div class="canvas-drop-slot tail" :class="{ active: isDropTarget(section.id, block.id, block.children.length) }" @dragover.prevent="setDropTarget(section.id, block.id, block.children.length)" @drop.stop="onBlockInsertDrop(section.id, block.id, block.children.length)" />
                        </div>
                      </template>

                      <template v-else>
                        <input class="canvas-block-title" :value="block.title" :placeholder="titlePlaceholder(block.kind)" @input="onBlockTitleInput(section.id, block.id, $event)" @click.stop />
                        <textarea class="canvas-block-body" :value="block.body || ''" :placeholder="bodyPlaceholder(block.kind)" @input="onBlockBodyInput(section.id, block.id, $event)" @click.stop />
                        <span v-if="block.link_to_section_id" class="block-link-badge">Lien vers une autre section</span>
                      </template>
                    </article>
                  </template>

                  <div v-if="section.blocks.length > 0" class="canvas-drop-slot tail" :class="{ active: isDropTarget(section.id, null, section.blocks.length) }" @dragover.prevent="setDropTarget(section.id, null, section.blocks.length)" @drop="onBlockInsertDrop(section.id, null, section.blocks.length)" />
                </div>
              </article>
            </div>
          </section>
        </div>
      </article>

      <aside class="card studio-inspector">
        <div class="inspector-head">
          <h2>Edition</h2>
          <button v-if="selection?.type === 'section' && draft.sections.length > 1" class="small danger" :disabled="busy" @click="removeSelectedSection">Supprimer section</button>
          <button v-if="selection?.type === 'block'" class="small danger" :disabled="busy" @click="removeSelectedBlock">Supprimer bloc</button>
        </div>

        <div v-if="!selection" class="empty">Selectionnez une section ou un bloc dans l'apercu.</div>

        <template v-else-if="selection.type === 'section' && selectedSection">
          <details class="inspector-panel" open>
            <summary>Navigation</summary>
            <div class="inspector-panel-body">
              <label><span>Slug</span><input v-model="selectedSection.slug" @input="touch" /></label>
              <label><span>Titre navigation</span><input v-model="selectedSection.nav_label" @input="touch" placeholder="Par defaut: titre section" /></label>
              <label><span>Groupe navigation</span><input v-model="selectedSection.nav_group" @input="touch" placeholder="Ex: Services" /></label>
              <label class="toggle"><input v-model="selectedSection.show_in_nav" type="checkbox" @change="touch" /><span>Afficher dans menu</span></label>
            </div>
          </details>

          <details class="inspector-panel" open>
            <summary>Disposition</summary>
            <div class="inspector-panel-body">
              <label>
                <span>Mode</span>
                <select v-model="selectedSection.layout" @change="touch">
                  <option value="vertical">Flex vertical</option>
                  <option value="horizontal">Flex horizontal</option>
                  <option value="grid">Grid</option>
                </select>
              </label>
              <label><span>Gap</span><input v-model.number="selectedSection.gap" type="number" min="0" max="80" @input="touch" /></label>
              <div class="fields three">
                <label><span>Padding</span><input v-model.number="selectedSection.padding" type="number" min="0" max="120" @input="touch" /></label>
                <label><span>Marge haute</span><input v-model.number="selectedSection.margin_top" type="number" min="0" max="160" @input="touch" /></label>
                <label><span>Marge basse</span><input v-model.number="selectedSection.margin_bottom" type="number" min="0" max="160" @input="touch" /></label>
              </div>
              <div class="fields two" v-if="selectedSection.layout === 'grid'">
                <label><span>Colonnes</span><input v-model.number="selectedSection.columns" type="number" min="1" max="6" @input="touch" /></label>
                <label><span>Lignes</span><input v-model.number="selectedSection.rows" type="number" min="1" max="12" @input="touch" /></label>
              </div>
              <label class="toggle"><input v-model="selectedSection.show_in_home" type="checkbox" @change="touch" /><span>Afficher sur accueil</span></label>
            </div>
          </details>
        </template>

        <template v-else-if="selection.type === 'block' && selectedBlock && selectedSection">
          <details class="inspector-panel" open>
            <summary>Bloc</summary>
            <div class="inspector-panel-body">
              <label>
                <span>Type</span>
                <select v-model="selectedBlock.kind" @change="touch">
                  <option value="heading">Titre</option>
                  <option value="text">Texte</option>
                  <option value="links">Liens</option>
                  <option value="cta">CTA</option>
                  <option value="machines_feed">Etat des machines</option>
                  <option value="image">Image</option>
                  <option value="banner">Banniere</option>
                  <option value="container">Container</option>
                  <option value="custom">Libre</option>
                </select>
              </label>
              <label v-if="selectedBlock.kind === 'image' || selectedBlock.kind === 'banner'"><span>URL image</span><input v-model="selectedBlock.image_url" @input="touch" placeholder="https://..." /></label>
              <label v-if="selectedBlock.kind === 'heading'"><span>Niveau de titre</span><select v-model.number="selectedBlock.heading_level" @change="touch"><option :value="1">H1</option><option :value="2">H2</option><option :value="3">H3</option><option :value="4">H4</option><option :value="5">H5</option><option :value="6">H6</option></select></label>
              <label><span>Lien vers section</span><select v-model="selectedBlock.link_to_section_id" @change="touch"><option :value="null">Aucun</option><option v-for="target in sectionTargets(selectedSection.id)" :key="target.id" :value="target.id">{{ target.title }}</option></select></label>
              <template v-if="selectedBlock.kind === 'container'">
                <label>
                  <span>Layout</span>
                  <select v-model="selectedBlock.container_layout" @change="touch">
                    <option value="vertical">Flex vertical</option>
                    <option value="horizontal">Flex horizontal</option>
                    <option value="grid">Grid</option>
                  </select>
                </label>
                <label><span>Gap interne</span><input v-model.number="selectedBlock.container_gap" type="number" min="0" max="80" @input="touch" /></label>
                <label v-if="selectedBlock.container_layout === 'grid'"><span>Colonnes</span><input v-model.number="selectedBlock.container_columns" type="number" min="1" max="6" @input="touch" /></label>
              </template>
            </div>
          </details>

          <details class="inspector-panel" open>
            <summary>Style</summary>
            <div class="inspector-panel-body">
              <div class="fields three">
                <label><span>Padding</span><input v-model.number="selectedBlock.padding" type="number" min="0" max="120" @input="touch" /></label>
                <label><span>Marge haute</span><input v-model.number="selectedBlock.margin_top" type="number" min="0" max="160" @input="touch" /></label>
                <label><span>Marge basse</span><input v-model.number="selectedBlock.margin_bottom" type="number" min="0" max="160" @input="touch" /></label>
              </div>
              <div class="fields two">
                <label><span>Taille police</span><input v-model.number="selectedBlock.font_size" type="number" min="10" max="64" @input="touch" /></label>
                <label><span>Police</span><select v-model="selectedBlock.font_family" @change="touch"><option v-for="font in fontOptions" :key="font.label" :value="font.value">{{ font.label }}</option></select></label>
              </div>
              <div class="fields two">
                <label><span>Couleur texte</span><input v-model="selectedBlock.text_color" type="color" @input="touch" /></label>
                <label><span>Fond</span><input v-model="selectedBlock.background_color" type="color" @input="touch" /></label>
              </div>
              <div class="fields three">
                <label><span>Bordure</span><input v-model="selectedBlock.border_color" type="color" @input="touch" /></label>
                <label><span>Epaisseur</span><input v-model.number="selectedBlock.border_width" type="number" min="0" max="24" @input="touch" /></label>
                <label><span>Rayon</span><input v-model.number="selectedBlock.border_radius" type="number" min="0" max="120" @input="touch" /></label>
              </div>
              <label><span>Alignement</span><select v-model="selectedBlock.text_align" @change="touch"><option value="left">Gauche</option><option value="center">Centre</option><option value="right">Droite</option></select></label>
            </div>
          </details>

          <details class="inspector-panel" open v-if="selectedSection.layout === 'grid'">
            <summary>Placement grid</summary>
            <div class="inspector-panel-body">
              <div class="fields two">
                <label><span>Span colonnes</span><input v-model.number="selectedBlock.span_cols" type="number" min="1" max="6" @input="touch" /></label>
                <label><span>Span lignes</span><input v-model.number="selectedBlock.span_rows" type="number" min="1" max="12" @input="touch" /></label>
              </div>
            </div>
          </details>
        </template>
      </aside>
    </section>
  </main>
</template>

<script setup lang="ts">
type LayoutMode = "vertical" | "horizontal" | "grid"
type TextAlign = "left" | "center" | "right"
type BlockKind = "heading" | "text" | "links" | "cta" | "machines_feed" | "image" | "banner" | "container" | "custom"
type CmsBlock = { id: string; title: string; body: string | null; image_url: string | null; kind: BlockKind; heading_level: number; span_cols: number; span_rows: number; padding: number; margin_top: number; margin_bottom: number; font_size: number; font_family: string | null; text_color: string | null; background_color: string | null; border_color: string | null; border_width: number; border_radius: number; text_align: TextAlign; link_to_section_id: string | null; container_layout: LayoutMode; container_columns: number; container_gap: number; children: CmsBlock[] }
type CmsSection = { id: string; title: string; slug: string; show_in_nav: boolean; nav_label: string | null; nav_group: string | null; show_in_home: boolean; layout: LayoutMode; columns: number; rows: number; gap: number; padding: number; margin_top: number; margin_bottom: number; blocks: CmsBlock[] }
type CmsDraft = { sections: CmsSection[] }
type CmsSiteBundle = { draft: CmsDraft; published: CmsDraft; published_version: number; updated_at: string | null; published_at: string | null }
type Selection = { type: "section"; sectionId: string } | { type: "block"; sectionId: string; blockId: string }
type BlockDragState = { sectionId: string; blockId: string }
type BlockDropTarget = { sectionId: string; containerId: string | null; blockIndex: number }
type BlockTemplateId = "heading" | "paragraph" | "button" | "links" | "machines_feed" | "image" | "banner" | "container" | "custom"

const config = useRuntimeConfig()
const backendBase = config.public.backendBase as string
const draft = reactive<CmsDraft>({ sections: [] })
const bundle = ref<CmsSiteBundle | null>(null)
const busy = ref(false)
const dirty = ref(false)
const msg = ref("")
const msgType = ref("")
const selection = ref<Selection | null>(null)
const sectionDragIndex = ref<number | null>(null)
const sectionPaletteDrag = ref(false)
const blockDrag = ref<BlockDragState | null>(null)
const paletteDragKind = ref<BlockTemplateId | null>(null)
const dropTarget = ref<BlockDropTarget | null>(null)

const blockPalette = [
  { kind: "heading", label: "Titre" },
  { kind: "paragraph", label: "Paragraphe" },
  { kind: "button", label: "Bouton" },
  { kind: "links", label: "Liens" },
  { kind: "machines_feed", label: "Etat machines" },
  { kind: "image", label: "Image" },
  { kind: "banner", label: "Banniere" },
  { kind: "container", label: "Container" },
  { kind: "custom", label: "Libre" },
] as const
const fontOptions = [
  { value: null, label: "Defaut" },
  { value: "Georgia, serif", label: "Georgia" },
  { value: "\"Times New Roman\", serif", label: "Times New Roman" },
  { value: "Arial, sans-serif", label: "Arial" },
  { value: "Verdana, sans-serif", label: "Verdana" },
  { value: "\"Trebuchet MS\", sans-serif", label: "Trebuchet MS" },
  { value: "\"Courier New\", monospace", label: "Courier New" },
]

const navSections = computed(() => draft.sections.filter((section) => section.show_in_nav))
const rootSection = computed(() => draft.sections.find((section) => section.id === "section-root") || draft.sections[0] || null)
const visibleSections = computed(() => draft.sections.filter((section) => section.id !== rootSection.value?.id))
const navPreviewItems = computed(() => {
  const items: Array<{ key: string; label: string }> = []
  const groups = new Map<string, string[]>()
  for (const section of navSections.value) {
    const label = section.nav_label || section.title
    const group = (section.nav_group || "").trim()
    if (!group) items.push({ key: section.id, label })
    else {
      if (!groups.has(group)) groups.set(group, [])
      groups.get(group)?.push(label)
    }
  }
  for (const [group, labels] of groups.entries()) items.push({ key: group, label: `${group} / ${labels.join(", ")}` })
  return items
})
const selectedSection = computed(() => !selection.value ? null : draft.sections.find((section) => section.id === selection.value!.sectionId) || null)
const selectedBlock = computed(() => !selection.value || selection.value.type !== "block" ? null : selectedSection.value ? findBlock(selectedSection.value.blocks, selection.value.blockId) : null)

function uid(prefix: string): string { return `${prefix}-${Math.random().toString(36).slice(2, 9)}` }
function slugify(value: string): string { return (value || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") }
function touch(): void { dirty.value = true }
function layoutLabel(layout: LayoutMode): string { return layout === "vertical" ? "flex vertical" : layout === "horizontal" ? "flex horizontal" : "grid" }
function hasVisibleSectionHeader(section: CmsSection): boolean { return Boolean((section.title || "").trim() || (section.nav_label || "").trim()) }
function bodyPlaceholder(kind: BlockKind): string { return kind === "container" ? "" : kind === "links" ? "Liste de liens, une ligne par entree" : kind === "cta" ? "Texte d'accroche et appel a l'action" : kind === "text" ? "Texte du bloc" : kind === "banner" ? "Texte de banniere" : "Contenu du bloc" }
function titlePlaceholder(kind: BlockKind): string { return kind === "heading" ? "Titre" : kind === "image" ? "Texte alternatif" : kind === "banner" ? "Titre optionnel" : "Titre" }
function fmtDate(value: string | null | undefined): string { if (!value) return "-"; const date = new Date(value); return Number.isNaN(date.valueOf()) ? String(value) : `${date.toLocaleDateString("fr-FR")} ${date.toLocaleTimeString("fr-FR")}` }
function isDropTarget(sectionId: string, containerId: string | null, blockIndex: number): boolean { return dropTarget.value?.sectionId === sectionId && dropTarget.value?.containerId === containerId && dropTarget.value?.blockIndex === blockIndex }
function inputValue(event: Event): string { const target = event.target; return target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement ? target.value : "" }

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${backendBase}${path}`, { headers: { "Content-Type": "application/json" }, ...options })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return (await response.json()) as T
}

function normalizeBlock(block: CmsBlock): CmsBlock {
  return {
    ...block,
    title: block.title ?? "",
    body: block.body ?? null,
    image_url: block.image_url ?? null,
    heading_level: block.heading_level ?? 2,
    padding: block.padding ?? 16,
    margin_top: block.margin_top ?? 0,
    margin_bottom: block.margin_bottom ?? 0,
    font_size: block.font_size ?? 16,
    font_family: block.font_family ?? null,
    text_color: block.text_color ?? null,
    background_color: block.background_color ?? null,
    border_color: block.border_color ?? null,
    border_width: block.border_width ?? 0,
    border_radius: block.border_radius ?? 0,
    text_align: block.text_align ?? "left",
    link_to_section_id: block.link_to_section_id ?? null,
    container_layout: block.container_layout ?? "vertical",
    container_columns: block.container_columns ?? 1,
    container_gap: block.container_gap ?? 16,
    children: (block.children ?? []).map(normalizeBlock),
  }
}

function normalizeDraft(next: CmsDraft): CmsDraft {
  const sections = next.sections.map((section) => ({
      ...section,
      nav_label: section.nav_label ?? null,
      nav_group: section.nav_group ?? null,
      padding: section.padding ?? 16,
      margin_top: section.margin_top ?? 0,
      margin_bottom: section.margin_bottom ?? 24,
      blocks: section.blocks.map(normalizeBlock),
    }))
  if (sections.length === 0) sections.push(createRootSection())
  if (!sections.some((section) => section.id === "section-root")) sections.unshift(createRootSection())
  return { sections }
}

function findBlock(blocks: CmsBlock[], blockId: string): CmsBlock | null {
  for (const block of blocks) {
    if (block.id === blockId) return block
    const nested = findBlock(block.children, blockId)
    if (nested) return nested
  }
  return null
}

function removeBlock(blocks: CmsBlock[], blockId: string): CmsBlock | null {
  const index = blocks.findIndex((block) => block.id === blockId)
  if (index >= 0) {
    const [removed] = blocks.splice(index, 1)
    return removed
  }
  for (const block of blocks) {
    const nested = removeBlock(block.children, blockId)
    if (nested) return nested
  }
  return null
}

function blockContainsId(block: CmsBlock, blockId: string): boolean {
  return block.id === blockId || block.children.some((child) => blockContainsId(child, blockId))
}

function targetBlocks(sectionId: string, containerId: string | null): CmsBlock[] | null {
  const section = draft.sections.find((item) => item.id === sectionId)
  if (!section) return null
  if (!containerId) return section.blocks
  const container = findBlock(section.blocks, containerId)
  return container?.kind === "container" ? container.children : null
}

function insertBlockAt(sectionId: string, containerId: string | null, blockIndex: number, block: CmsBlock): boolean {
  const blocks = targetBlocks(sectionId, containerId)
  if (!blocks) return false
  blocks.splice(blockIndex, 0, block)
  return true
}

function insertSectionAt(index: number): void {
  const section = createSection()
  const targetIndex = Math.max(0, Math.min(index, draft.sections.length))
  draft.sections.splice(targetIndex, 0, section)
  selection.value = { type: "section", sectionId: section.id }
  sectionPaletteDrag.value = false
  touch()
}

function setDraft(next: CmsDraft): void { const normalized = normalizeDraft(next); draft.sections.splice(0, draft.sections.length, ...normalized.sections) }
async function reload(): Promise<void> { busy.value = true; try { const next = await api<CmsSiteBundle>("/cms/frontoffice"); bundle.value = next; setDraft(structuredClone(next.draft)); selection.value = draft.sections[0] ? { type: "section", sectionId: draft.sections[0].id } : null; dirty.value = false; msg.value = "Brouillon charge."; msgType.value = "ok" } catch (error) { msg.value = error instanceof Error ? error.message : "Erreur"; msgType.value = "err" } finally { busy.value = false } }
async function saveDraft(): Promise<void> { busy.value = true; try { const next = await api<CmsSiteBundle>("/cms/frontoffice/draft", { method: "PUT", body: JSON.stringify(draft) }); bundle.value = next; dirty.value = false; msg.value = "Brouillon sauvegarde."; msgType.value = "ok" } catch (error) { msg.value = error instanceof Error ? error.message : "Erreur"; msgType.value = "err" } finally { busy.value = false } }
async function publish(): Promise<void> { if (dirty.value) await saveDraft(); busy.value = true; try { const next = await api<CmsSiteBundle>("/cms/frontoffice/publish", { method: "POST" }); bundle.value = next; msg.value = "Publication effectuee."; msgType.value = "ok" } catch (error) { msg.value = error instanceof Error ? error.message : "Erreur"; msgType.value = "err" } finally { busy.value = false } }

function createSection(): CmsSection { const id = uid("section"); return { id, title: " ", slug: id, show_in_nav: false, nav_label: null, nav_group: null, show_in_home: true, layout: "vertical", columns: 1, rows: 1, gap: 16, padding: 16, margin_top: 0, margin_bottom: 24, blocks: [] } }
function createRootSection(): CmsSection { return { id: "section-root", title: " ", slug: "section-root", show_in_nav: false, nav_label: null, nav_group: null, show_in_home: true, layout: "vertical", columns: 1, rows: 1, gap: 16, padding: 16, margin_top: 0, margin_bottom: 24, blocks: [] } }
function defaultBodyForKind(kind: BlockKind): string | null { return kind === "machines_feed" || kind === "image" || kind === "container" ? null : kind === "banner" ? "Texte de banniere" : kind === "links" ? "Lien 1\nLien 2" : kind === "cta" ? "Votre message d'action" : kind === "text" ? "Votre texte ici" : "Contenu" }
function createBlock(kind: BlockKind = "custom"): CmsBlock { return { id: uid("block"), title: kind === "heading" ? "Titre" : kind === "machines_feed" ? "Etat des machines" : kind === "image" ? "" : kind === "banner" ? "" : kind === "container" ? "" : "Nouveau bloc", body: defaultBodyForKind(kind), image_url: null, kind, heading_level: 2, span_cols: 1, span_rows: 1, padding: kind === "banner" || kind === "image" || kind === "container" || kind === "heading" ? 0 : 16, margin_top: 0, margin_bottom: 0, font_size: kind === "heading" ? 40 : kind === "banner" ? 24 : 16, font_family: null, text_color: null, background_color: null, border_color: null, border_width: 0, border_radius: 0, text_align: "left", link_to_section_id: null, container_layout: "vertical", container_columns: 1, container_gap: 16, children: [] } }
function createBlockFromTemplate(template: BlockTemplateId): CmsBlock {
  if (template === "heading") return { ...createBlock("heading"), title: "Titre", body: null, padding: 0, font_size: 40, margin_bottom: 8 }
  if (template === "paragraph") return { ...createBlock("text"), title: "", body: "Votre paragraphe ici", padding: 0, font_size: 16 }
  if (template === "button") return { ...createBlock("cta"), title: "Bouton", body: "Call to action", padding: 12, font_size: 16 }
  if (template === "links") return createBlock("links")
  if (template === "machines_feed") return createBlock("machines_feed")
  if (template === "image") return createBlock("image")
  if (template === "banner") return createBlock("banner")
  if (template === "container") return createBlock("container")
  return createBlock("custom")
}
function addSection(): void { const section = createSection(); draft.sections.push(section); selection.value = { type: "section", sectionId: section.id }; touch() }
function selectSection(sectionId: string): void { selection.value = { type: "section", sectionId } }
function selectBlock(sectionId: string, blockId: string): void { selection.value = { type: "block", sectionId, blockId } }
function updateSectionTitle(sectionId: string, value: string): void { const section = draft.sections.find((item) => item.id === sectionId); if (!section) return; section.title = value; if (!section.slug || section.slug.startsWith("section-")) section.slug = slugify(value) || section.id; touch() }
function updateBlockTitle(sectionId: string, blockId: string, value: string): void { const section = draft.sections.find((item) => item.id === sectionId); const block = section ? findBlock(section.blocks, blockId) : null; if (!block) return; block.title = value; touch() }
function updateBlockBody(sectionId: string, blockId: string, value: string): void { const section = draft.sections.find((item) => item.id === sectionId); const block = section ? findBlock(section.blocks, blockId) : null; if (!block) return; block.body = value; touch() }
function onSectionTitleInput(sectionId: string, event: Event): void { updateSectionTitle(sectionId, inputValue(event)) }
function onBlockTitleInput(sectionId: string, blockId: string, event: Event): void { updateBlockTitle(sectionId, blockId, inputValue(event)) }
function onBlockBodyInput(sectionId: string, blockId: string, event: Event): void { updateBlockBody(sectionId, blockId, inputValue(event)) }
function removeSelectedSection(): void { if (!selectedSection.value || draft.sections.length <= 1) return; const index = draft.sections.findIndex((section) => section.id === selectedSection.value!.id); if (index < 0) return; draft.sections.splice(index, 1); selection.value = draft.sections[0] ? { type: "section", sectionId: draft.sections[0].id } : null; touch() }
function removeSelectedBlock(): void { if (!selectedSection.value || !selectedBlock.value) return; if (!removeBlock(selectedSection.value.blocks, selectedBlock.value.id)) return; selection.value = selectedSection.value.id === "section-root" ? null : { type: "section", sectionId: selectedSection.value.id }; touch() }
function onSectionPaletteDragStart(): void { sectionPaletteDrag.value = true; paletteDragKind.value = null }
function onPaletteDragStart(kind: BlockTemplateId): void { paletteDragKind.value = kind }
function onCanvasStackDrop(): void {
  if (!rootSection.value) return
  if (paletteDragKind.value) insertPaletteBlock(rootSection.value.id, null, rootSection.value.blocks.length)
}
function setDropTarget(sectionId: string, containerId: string | null, blockIndex: number): void { dropTarget.value = { sectionId, containerId, blockIndex } }
function parentDropIndex(sectionId: string, containerId: string | null, layout: LayoutMode, event: DragEvent): number {
  const blocks = targetBlocks(sectionId, containerId)
  if (!blocks) return 0
  if (blocks.length === 0) return 0
  const target = event.currentTarget
  if (!(target instanceof HTMLElement)) return blocks.length
  const rect = target.getBoundingClientRect()
  if (layout === "horizontal") return event.clientX < rect.left + rect.width / 2 ? 0 : blocks.length
  return event.clientY < rect.top + rect.height / 2 ? 0 : blocks.length
}
function onParentHover(sectionId: string, containerId: string | null, layout: LayoutMode, event: DragEvent): void {
  setDropTarget(sectionId, containerId, parentDropIndex(sectionId, containerId, layout, event))
}
function onParentDrop(sectionId: string, containerId: string | null, layout: LayoutMode, event: DragEvent): void {
  if (sectionPaletteDrag.value) {
    if (sectionId === rootSection.value?.id && containerId === null) insertSectionAt(draft.sections.length)
    sectionPaletteDrag.value = false
    dropTarget.value = null
    return
  }
  onBlockInsertDrop(sectionId, containerId, parentDropIndex(sectionId, containerId, layout, event))
}
function insertPaletteBlock(sectionId: string, containerId: string | null, blockIndex: number): void {
  if (!paletteDragKind.value) return
  const block = createBlockFromTemplate(paletteDragKind.value)
  if (!insertBlockAt(sectionId, containerId, blockIndex, block)) return
  selection.value = { type: "block", sectionId, blockId: block.id }
  paletteDragKind.value = null
  dropTarget.value = null
  touch()
}
function onEmptySectionDrop(sectionId: string): void {
  if (sectionPaletteDrag.value) {
    if (sectionId === rootSection.value?.id) insertSectionAt(draft.sections.length)
    return
  }
  insertPaletteBlock(sectionId, null, 0)
}
function onSectionCanvasDrop(sectionId: string): void {
  if (sectionPaletteDrag.value) {
    if (sectionId === rootSection.value?.id) insertSectionAt(draft.sections.length)
    return
  }
  if ((draft.sections.find((section) => section.id === sectionId)?.blocks.length ?? 0) === 0) insertPaletteBlock(sectionId, null, 0)
}
function onBlockInsertDrop(sectionId: string, containerId: string | null, blockIndex: number): void {
  if (paletteDragKind.value) return insertPaletteBlock(sectionId, containerId, blockIndex)
  const source = blockDrag.value
  blockDrag.value = null
  dropTarget.value = null
  if (!source || source.sectionId !== sectionId) return
  const section = draft.sections.find((item) => item.id === sectionId)
  if (!section) return
  const dragged = findBlock(section.blocks, source.blockId)
  if (!dragged) return
  if (containerId && blockContainsId(dragged, containerId)) return
  const moved = removeBlock(section.blocks, source.blockId)
  if (!moved) return
  const target = targetBlocks(sectionId, containerId)
  if (!target) return
  const targetIndex = Math.max(0, Math.min(blockIndex, target.length))
  target.splice(targetIndex, 0, moved)
  selection.value = { type: "block", sectionId, blockId: moved.id }
  touch()
}
function onSectionDragStart(sectionIndex: number): void { sectionDragIndex.value = sectionIndex }
function onSectionDrop(targetIndex: number): void {
  if (sectionPaletteDrag.value) {
    sectionPaletteDrag.value = false
    return
  }
  const sourceIndex = sectionDragIndex.value
  sectionDragIndex.value = null
  sectionPaletteDrag.value = false
  if (sourceIndex === null || sourceIndex === targetIndex) return
  const [item] = draft.sections.splice(sourceIndex, 1)
  draft.sections.splice(targetIndex, 0, item)
  touch()
}
function onBlockDragStart(sectionId: string, blockId: string): void { blockDrag.value = { sectionId, blockId } }
function sectionTargets(selfId: string): CmsSection[] { return draft.sections.filter((section) => section.id !== selfId) }
function sectionCardStyle(section: CmsSection): Record<string, string> { return { marginTop: `${section.margin_top}px`, marginBottom: `${section.margin_bottom}px` } }
function sectionStyle(section: CmsSection): Record<string, string> { if (section.layout === "grid") return { display: "grid", gap: `${section.gap}px`, gridTemplateColumns: `repeat(${Math.max(1, section.columns)}, minmax(0, 1fr))`, gridAutoRows: "minmax(140px, auto)", padding: `${section.padding}px` }; if (section.layout === "horizontal") return { display: "grid", gap: `${section.gap}px`, gridAutoFlow: "column", gridAutoColumns: "minmax(240px, 1fr)", overflowX: "auto", padding: `${section.padding}px` }; return { display: "grid", gap: `${section.gap}px`, padding: `${section.padding}px` } }
function containerStyle(block: CmsBlock): Record<string, string> { if (block.container_layout === "grid") return { display: "grid", gap: `${block.container_gap}px`, gridTemplateColumns: `repeat(${Math.max(1, block.container_columns)}, minmax(0, 1fr))`, gridAutoRows: "minmax(120px, auto)" }; if (block.container_layout === "horizontal") return { display: "grid", gap: `${block.container_gap}px`, gridAutoFlow: "column", gridAutoColumns: "minmax(240px, 1fr)", overflowX: "auto" }; return { display: "grid", gap: `${block.container_gap}px` } }
function blockStyle(section: CmsSection, block: CmsBlock): Record<string, string> { const style: Record<string, string> = { padding: `${block.kind === "banner" || block.kind === "image" ? 0 : block.padding}px`, marginTop: `${block.margin_top}px`, marginBottom: `${block.margin_bottom}px`, fontSize: `${block.font_size}px`, textAlign: block.text_align }; if (block.font_family) style.fontFamily = block.font_family; if (block.text_color) style.color = block.text_color; if (block.background_color) style.backgroundColor = block.background_color; if (block.border_color) style.borderColor = block.border_color; if (block.border_width > 0) { style.borderWidth = `${block.border_width}px`; style.borderStyle = "solid" }; if (block.border_radius > 0) style.borderRadius = `${block.border_radius}px`; if (block.kind === "container") Object.assign(style, containerStyle(block)); if (section.layout !== "grid") return style; return { ...style, gridColumn: `span ${Math.max(1, block.span_cols)}`, gridRow: `span ${Math.max(1, block.span_rows)}` } }
function bannerStyle(block: CmsBlock): Record<string, string> { const background = block.image_url ? `linear-gradient(rgba(23,34,35,0.4), rgba(23,34,35,0.22)), url("${block.image_url}") center / cover` : "linear-gradient(135deg, rgba(13,102,96,0.92), rgba(11,74,70,0.92))"; const style: Record<string, string> = { background, padding: "0px" }; if (block.font_family) style.fontFamily = block.font_family; return style }
function isTypingTarget(target: EventTarget | null): boolean { return target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement || (target instanceof HTMLElement && target.isContentEditable) }
function onWindowKeydown(event: KeyboardEvent): void {
  if (event.key !== "Delete" || isTypingTarget(event.target) || !selection.value) return
  if (selection.value.type === "block") {
    if (!selectedBlock.value || !window.confirm("Supprimer ce bloc ?")) return
    event.preventDefault()
    removeSelectedBlock()
    return
  }
  if (!selectedSection.value || selectedSection.value.id === "section-root" || !window.confirm("Supprimer cette section ?")) return
  event.preventDefault()
  removeSelectedSection()
}

watch(() => draft.sections.map((section) => section.title), () => { for (const section of draft.sections) { if (!section.slug || section.slug.startsWith("section-")) section.slug = slugify(section.title) || section.id } }, { deep: true })
onMounted(() => { reload(); window.addEventListener("keydown", onWindowKeydown) })
onBeforeUnmount(() => { window.removeEventListener("keydown", onWindowKeydown) })
</script>

<style scoped>
.block-palette {
  position: sticky;
  top: 24px;
  z-index: 5;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid #d8dde5;
  border-radius: 14px;
  background: rgba(251, 252, 253, 0.96);
  backdrop-filter: blur(8px);
}

.canvas-root {
  display: grid;
  gap: 14px;
  padding: 18px;
  border: 1px solid #d8dde5;
  border-radius: 18px;
  background: linear-gradient(180deg, #fbfcfd, #f5f7fa);
}

.canvas-root-head {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #7b838f;
}

.canvas-root-sections {
  display: grid;
  gap: 14px;
}

.canvas-grid-root {
  min-height: 120px;
  align-content: start;
}

.canvas-container-drop {
  display: grid;
  gap: 12px;
  min-height: 120px;
  padding: 14px;
  border: 1px solid #d6d9de;
  border-radius: 14px;
  background: #f8f9fb;
}

.canvas-drop-slot {
  min-height: 18px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.14);
  transition: background-color 120ms ease, min-height 120ms ease;
}

.canvas-drop-slot.active {
  min-height: 24px;
  background: rgba(148, 163, 184, 0.38);
}

.canvas-drop-slot.tail {
  margin-bottom: 4px;
}

.canvas-empty-drop {
  min-height: 84px;
  display: grid;
  place-items: center;
  border: 1px dashed #c9ced6;
  border-radius: 12px;
  color: #6b7280;
  background: rgba(255, 255, 255, 0.7);
  text-align: center;
}

.canvas-block {
  border-radius: 14px;
}

.canvas-block-child {
  background: #ffffff;
}

</style>
